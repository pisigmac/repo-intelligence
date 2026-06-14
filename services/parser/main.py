"""Parser Service: language detection, AST extraction, file classification, dependency graph."""
import os
import sys
import re
import json
import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

sys.path.insert(0, "/app")
from libs.common import configure_logging, get_settings, KafkaProducer, KafkaConsumer
from services.parser.models import ParsedFile, ParsedRepo
from services.parser.language import detect_language
from services.parser.javascript import parse_javascript
from services.parser.static import parse_static
from libs.utils import get_repo_files, read_file_safe

settings = get_settings()
logger = configure_logging(settings.app_name, settings.log_level)

# File classification patterns
CLASSIFICATION_PATTERNS = {
    "route": re.compile(r'router\.(get|post|put|delete|patch|use)\s*\(', re.IGNORECASE),
    "middleware": re.compile(r'(middleware|verifyToken|authenticate|auth)', re.IGNORECASE),
    "test": re.compile(r'\.(test|spec)\.(js|ts|py)', re.IGNORECASE),
    "config": re.compile(r'(config|setup|webpack|babel|eslint|prettier|dockerfile|ci/cd)', re.IGNORECASE),
    "controller": re.compile(r'(controller|handler|service)', re.IGNORECASE),
}


def parse_python(file_path: Path, content: str) -> dict[str, Any]:
    lines = content.splitlines()
    loc = len([l for l in lines if l.strip() and not l.strip().startswith("#")])

    import_pattern = re.compile(r"^(?:from|import)\s+([\w.]+)")
    deps = [m for m in import_pattern.findall(content) if not m.startswith(".")]

    func_pattern = re.compile(r"(?:async\s+)?def\s+(\w+)\(([^)]*)\):")
    functions = []
    for match in func_pattern.finditer(content):
        functions.append({
            "name": match.group(1),
            "signature": f"{match.group(1)}({match.group(2)})",
            "async": "async" in content[max(0, match.start()-10):match.start()],
        })

    class_pattern = re.compile(r"class\s+(\w+)(?:\(([^)]*)\))?:")
    classes = [{"name": m[0], "extends": m[1]} for m in class_pattern.findall(content)]

    return {
        "language": "python",
        "lines_of_code": loc,
        "functions": functions,
        "classes": classes,
        "dependencies": list(set(deps)),
    }


def parse_file(file_path: Path) -> ParsedFile | None:
    content = read_file_safe(file_path)
    if content is None:
        return None

    lang = detect_language(file_path)
    classification = classify_file(file_path, content)

    if lang in ("javascript", "typescript"):
        ast = parse_javascript(file_path, content)
    elif lang == "python":
        ast = parse_python(file_path, content)
    else:
        ast = parse_static(file_path, lang, content)

    return ParsedFile(
        path=str(file_path),
        language=lang,
        classification=classification,
        ast_summary=ast,
        dependencies=ast.get("dependencies", []),
        lines_of_code=ast.get("lines_of_code", 0),
    )


def build_dependency_graph(files: list[ParsedFile]) -> dict[str, list[str]]:
    """Build a simple file-to-file dependency graph based on local imports."""
    graph: dict[str, list[str]] = {}
    path_map = {f.path: f for f in files}

    for f in files:
        local_deps = []
        for dep in f.dependencies:
            if dep.startswith(".") or dep.startswith("/"):
                # Try to resolve local file
                base = Path(f.path).parent
                candidate = base / dep
                if not candidate.suffix:
                    for ext in [".js", ".ts", ".jsx", ".tsx", ".py"]:
                        if str(candidate.with_suffix(ext)) in path_map:
                            local_deps.append(str(candidate.with_suffix(ext)))
                            break
                elif str(candidate) in path_map:
                    local_deps.append(str(candidate))
        graph[f.path] = local_deps
    return graph


async def handle_repo_ingested(topic: str, message: dict):
    """Kafka consumer handler for repo.ingested events."""
    data = message.get("data", {})
    repo_id = data.get("repo_id")
    storage_path = data.get("storage_path")
    commit = data.get("commit")

    if not repo_id or not storage_path:
        logger.warning("Invalid repo.ingested message", extra={"payload": message})
        return

    logger.info("Parsing repo", extra={"repo_id": repo_id, "path": storage_path})

    try:
        files = get_repo_files(storage_path)
        parsed_files: list[ParsedFile] = []

        for file_path in files:
            pf = parse_file(file_path)
            if pf:
                parsed_files.append(pf)

        graph = build_dependency_graph(parsed_files)

        parsed_repo = ParsedRepo(
            repo_id=repo_id,
            commit=commit,
            files=parsed_files,
            dependency_graph=graph,
        )

        # Write parsed output to disk for downstream services
        output_dir = os.path.join(settings.repo_storage_path, "parsed", repo_id)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "parsed.json")
        with open(output_path, "w") as f:
            f.write(parsed_repo.model_dump_json(indent=2))

        # Emit repo.parsed event
        event = {
            "specversion": "1.0",
            "type": "repo.parsed",
            "source": "parser-service",
            "id": message.get("id", str(datetime.utcnow())),
            "time": datetime.utcnow().isoformat() + "Z",
            "datacontenttype": "application/json",
            "data": {
                "repo_id": repo_id,
                "commit": commit,
                "parsed_path": output_path,
                "file_count": len(parsed_files),
                "languages": list(set(f.language for f in parsed_files)),
            },
        }
        await producer.send("repo.parsed", event, key=repo_id)
        logger.info(
            "Repo parsed and event emitted",
            extra={"repo_id": repo_id, "files": len(parsed_files)},
        )
    except Exception:
        logger.exception("Parsing failed", extra={"repo_id": repo_id})


# Global producer for event emission
producer: KafkaProducer | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global producer
    producer = KafkaProducer(settings.kafka_bootstrap_servers)
    await producer.start()

    # Start Kafka consumer in background
    consumer = KafkaConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        topics=["repo.ingested"],
        group_id=f"{settings.kafka_group_id}-parser",
        handler=handle_repo_ingested,
    )
    await consumer.start()

    # Run consumer as background task
    task = asyncio.create_task(consumer.run())
    logger.info("Parser service started")

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await consumer.stop()
    await producer.stop()
    logger.info("Parser service stopped")

app = FastAPI(title="Parser Service", version="1.0.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "parser"}

@app.get("/parse/{repo_id}")
async def get_parsed(repo_id: str):
    output_path = os.path.join(settings.repo_storage_path, "parsed", repo_id, "parsed.json")
    if not os.path.exists(output_path):
        return {"status": "not_found"}
    with open(output_path, "r") as f:
        return json.load(f)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
