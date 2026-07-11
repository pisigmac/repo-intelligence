"""Analysis Service: semantic understanding, API extraction, dependency graph enrichment."""
import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Any
import uuid

from fastapi import FastAPI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

sys.path.insert(0, "/app")
from libs.common import configure_logging, get_settings, KafkaProducer, KafkaConsumer
from libs.common.embeddings import get_embedding

settings = get_settings()
logger = configure_logging(settings.app_name, settings.log_level)


class SemanticAnalyzer:
    def __init__(self):
        self.qdrant = QdrantClient(url=settings.qdrant_url)
        self.collection_name = "repo_embeddings"
        self._ensure_collection()

    def _ensure_collection(self):
        try:
            self.qdrant.get_collection(self.collection_name)
        except Exception:
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
            logger.info("Created Qdrant collection", extra={"name": self.collection_name})

    def store_embedding(self, id: str, text: str, metadata: dict):
        vec = get_embedding(text)
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, id))
        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=[PointStruct(id=point_id, vector=vec, payload=metadata)],
        )

    def search(self, query: str, limit: int = 5) -> list[dict]:
        vec = get_embedding(query)
        results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=vec,
            limit=limit,
        )
        return [{"id": r.id, "score": r.score, "payload": r.payload} for r in results]


def extract_apis_from_parsed(parsed: dict) -> list[dict]:
    """Extract API surface from parsed files."""
    apis = []
    for f in parsed.get("files", []):
        ast = f.get("ast_summary", {})
        for route in ast.get("routes", []):
            apis.append({
                "file": f["path"],
                "method": route["method"],
                "path": route["path"],
                "type": "http_endpoint",
            })
        for func in ast.get("functions", []):
            if "export" in str(ast.get("exports", [])).lower() or f["classification"] in ["route", "middleware", "controller"]:
                apis.append({
                    "file": f["path"],
                    "name": func["name"],
                    "signature": func.get("signature", ""),
                    "type": "function",
                })
    return apis


def build_semantic_chunks(parsed: dict) -> list[dict]:
    """Build searchable text chunks from parsed repo."""
    chunks = []
    repo_id = parsed.get("repo_id", "unknown")
    for f in parsed.get("files", []):
        ast = f.get("ast_summary", {})
        # File-level chunk
        chunks.append({
            "id": f"{repo_id}::{f['path']}::file",
            "text": f"File {f['path']} is a {f['classification']} written in {f['language']}. "
                    f"It has {ast.get('lines_of_code', 0)} lines of code.",
            "metadata": {"repo_id": repo_id, "path": f["path"], "type": "file"},
        })
        # Function-level chunks
        for func in ast.get("functions", []):
            chunks.append({
                "id": f"{repo_id}::{f['path']}::func::{func['name']}",
                "text": f"Function {func['name']} in {f['path']}: {func.get('signature', '')}",
                "metadata": {"repo_id": repo_id, "path": f["path"], "func": func["name"], "type": "function"},
            })
        # Route-level chunks
        for route in ast.get("routes", []):
            chunks.append({
                "id": f"{repo_id}::{f['path']}::route::{route['method']}:{route['path']}",
                "text": f"HTTP {route['method']} endpoint at {route['path']} defined in {f['path']}",
                "metadata": {"repo_id": repo_id, "path": f["path"], "method": route["method"], "path": route["path"], "type": "route"},
            })
    return chunks


async def handle_repo_parsed(topic: str, message: dict):
    data = message.get("data", {})
    repo_id = data.get("repo_id")
    parsed_path = data.get("parsed_path")

    if not repo_id or not parsed_path or not os.path.exists(parsed_path):
        logger.warning("Invalid repo.parsed message", extra={"payload": message})
        return

    logger.info("Analyzing repo", extra={"repo_id": repo_id})

    try:
        with open(parsed_path, "r") as f:
            parsed = json.load(f)

        analyzer = SemanticAnalyzer()

        # Store embeddings
        chunks = build_semantic_chunks(parsed)
        for chunk in chunks:
            analyzer.store_embedding(chunk["id"], chunk["text"], chunk["metadata"])

        # Extract APIs
        apis = extract_apis_from_parsed(parsed)

        # Write analysis output
        output_dir = os.path.join(settings.repo_storage_path, "analyzed", repo_id)
        os.makedirs(output_dir, exist_ok=True)
        analysis_path = os.path.join(output_dir, "analysis.json")
        analysis = {
            "repo_id": repo_id,
            "commit": parsed.get("commit"),
            "apis": apis,
            "chunk_count": len(chunks),
            "dependency_graph": parsed.get("dependency_graph", {}),
        }
        with open(analysis_path, "w") as f:
            json.dump(analysis, f, indent=2)

        # Emit event
        event = {
            "specversion": "1.0",
            "type": "repo.analyzed",
            "source": "analysis-service",
            "id": message.get("id", str(datetime.utcnow())),
            "time": datetime.utcnow().isoformat() + "Z",
            "datacontenttype": "application/json",
            "data": {
                "repo_id": repo_id,
                "analysis_path": analysis_path,
                "api_count": len(apis),
            },
        }
        await producer.send("repo.analyzed", event, key=repo_id)
        logger.info("Analysis complete", extra={"repo_id": repo_id, "apis": len(apis)})
    except Exception:
        logger.exception("Analysis failed", extra={"repo_id": repo_id})


producer: KafkaProducer | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global producer
    producer = KafkaProducer(settings.kafka_bootstrap_servers)
    await producer.start()

    consumer = KafkaConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        topics=["repo.parsed"],
        group_id=f"{settings.kafka_group_id}-analysis",
        handler=handle_repo_parsed,
    )
    await consumer.start()
    task = asyncio.create_task(consumer.run())
    logger.info("Analysis service started")

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await consumer.stop()
    await producer.stop()

app = FastAPI(title="Analysis Service", version="1.0.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "analysis"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
