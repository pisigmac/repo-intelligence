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
from libs.utils import get_repo_files, read_file_safe

settings = get_settings()
logger = configure_logging(settings.app_name, settings.log_level)

# Language mapping
EXTENSION_MAP = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".py": "python",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
}

# File classification patterns
CLASSIFICATION_PATTERNS = {
    "route": re.compile(r'router\.(get|post|put|delete|patch|use)\s*\(', re.IGNORECASE),
    "middleware": re.compile(r'(middleware|verifyToken|authenticate|auth)', re.IGNORECASE),
    "test": re.compile(r'\.(test|spec)\.(js|ts|py)', re.IGNORECASE),
    "config": re.compile(r'(config|setup|webpack|babel|eslint|prettier|dockerfile|ci/cd)', re.IGNORECASE),
    "controller": re.compile(r'(controller|handler|service)', re.IGNORECASE),
}

# JS Parsing regexes
JS_PATTERNS = {
    "require": re.compile(r'''require\s*\(\s*['"]([^'"]+)['"]\s*\)'''),
    "import": re.compile(r'''import\s+(?:(?:\{[^}]*\}|[\w*]+)\s+from\s+)?['"]([^'"]+)['"];?'''),
    "function_decl": re.compile(r"(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)"),
    "arrow_function": re.compile(r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=]+)\s*=>"),
    "method": re.compile(r"(\w+)\s*\(([^)]*)\)\s*\{"),
    "express_route": re.compile(r'''(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*['"]([^'"]+)['"]'''),
    "middleware_use": re.compile(r"(?:app|router)\.use\s*\(\s*([^)]+)\)"),
    "class_decl": re.compile(r"class\s+(\w+)(?:\s+extends\s+(\w+))?"),
    "export": re.compile(r"module\.exports\s*=\s*(\w+)"),
}


class ParsedFile(BaseModel):
    path: str
    language: str
    classification: str
    ast_summary: dict[str, Any]
    dependencies: list[str]
    lines_of_code: int


class ParsedRepo(BaseModel):
    repo_id: str
    commit: str
    files: list[ParsedFile]
    dependency_graph: dict[str, list[str]]


def detect_language(file_path: Path) -> str:
    return EXTENSION_MAP.get(file_path.suffix.lower(), "unknown")


def classify_file(file_path: Path, content: str) -> str:
    # Check filename first
    fname = file_path.name.lower()
    if CLASSIFICATION_PATTERNS["test"].search(fname):
        return "test"
    if "middleware" in fname:
        return "middleware"
    if "route" in fname:
        return "route"
    if "config" in fname:
        return "config"

    # Check content patterns
    scores = {}
    for category, pattern in CLASSIFICATION_PATTERNS.items():
        scores[category] = len(pattern.findall(content))

    if scores:
        best = max(scores, key=scores.get)
        if scores[best] > 0:
            return best
    return "utility"


def parse_javascript(file_path: Path, content: str) -> dict[str, Any]:
    """Extract AST-like summary from JavaScript using robust regex parsing."""
    lines = content.splitlines()
    loc = len([l for l in lines if l.strip() and not l.strip().startswith("//")])

    deps = []
    deps.extend(JS_PATTERNS["require"].findall(content))
    deps.extend(JS_PATTERNS["import"].findall(content))

    functions = []
    for match in JS_PATTERNS["function_decl"].finditer(content):
        functions.append({
            "type": "function",
            "name": match.group(1),
            "signature": f"{match.group(1)}({match.group(2)})",
            "async": "async" in content[max(0, match.start()-10):match.start()],
        })

    for match in JS_PATTERNS["arrow_function"].finditer(content):
        functions.append({
            "type": "arrow_function",
            "name": match.group(1),
            "signature": f"{match.group(1)}()",
            "async": False,
        })

    routes = []
    for match in JS_PATTERNS["express_route"].finditer(content):
        routes.append({
            "method": match.group(1).upper(),
            "path": match.group(2),
        })

    middlewares = []
    for match in JS_PATTERNS["middleware_use"].finditer(content):
        middlewares.append(match.group(1).strip())

    classes = []
    for match in JS_PATTERNS["class_decl"].finditer(content):
        classes.append({
            "name": match.group(1),
            "extends": match.group(2),
        })

    exports = JS_PATTERNS["export"].findall(content)

    return {
        "language": "javascript",
        "lines_of_code": loc,
        "functions": functions,
        "routes": routes,
        "middlewares": middlewares,
        "classes": classes,
        "exports": exports,
        "dependencies": list(set(deps)),
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

    if lang == "javascript":
        ast = parse_javascript(file_path, content)
    elif lang == "python":
        ast = parse_python(file_path, content)
    else:
        lines = content.splitlines()
        loc = len([l for l in lines if l.strip()])
        ast = {
            "language": lang,
            "lines_of_code": loc,
            "functions": [],
            "classes": [],
            "dependencies": [],
        }

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
