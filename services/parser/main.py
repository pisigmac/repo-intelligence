"""Parser Service: language detection, AST extraction, file classification, dependency graph."""
import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI

sys.path.insert(0, "/app")
from libs.common import configure_logging, get_settings, KafkaProducer, KafkaConsumer
from services.parser.models import ParsedFile, ParsedRepo
from services.parser.graph import build_dependency_graph
from services.parser.core import parse_file
from libs.utils import get_repo_files

settings = get_settings()
logger = configure_logging(settings.app_name, settings.log_level)





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

        graph = build_dependency_graph(parsed_files, repo_root=storage_path)

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
