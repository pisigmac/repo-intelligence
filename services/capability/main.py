"""Capability Service: extracts system capabilities from analyzed repos."""
import os
import sys
import json
import uuid
import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from sqlalchemy import text

sys.path.insert(0, "/app")
from libs.common import configure_logging, get_settings, KafkaProducer, KafkaConsumer, engine, Base
from libs.models import Capability, EntryPoint

settings = get_settings()
logger = configure_logging(settings.app_name, settings.log_level)


def extract_capabilities(analysis: dict, repo_id: str, commit: str) -> list[Capability]:
    """Extract capabilities from analysis output."""
    capabilities = []
    apis = analysis.get("apis", [])

    # Group APIs by functional area
    auth_apis = [a for a in apis if any(k in a.get("name", "").lower() + a.get("file", "").lower() for k in ["auth", "login", "register", "token", "verify", "jwt"])]
    route_apis = [a for a in apis if a.get("type") == "http_endpoint"]
    middleware_apis = [a for a in apis if "middleware" in a.get("file", "").lower() or "verify" in a.get("name", "").lower()]

    if auth_apis:
        entry_points = []
        for a in auth_apis:
            if a.get("type") == "http_endpoint":
                entry_points.append(EntryPoint(method=a.get("method"), path=a.get("path"), file=a.get("file")))

        interfaces = {}
        for a in auth_apis:
            if a.get("type") == "function":
                interfaces[a["name"]] = {"signature": a.get("signature", ""), "file": a["file"]}

        capabilities.append(Capability(
            id=f"cap_auth_{repo_id[:8]}",
            name="JWT Authentication",
            description="User registration, login, and JWT token verification system",
            category="auth",
            repo=repo_id,
            commit=commit,
            entry_points=entry_points,
            interfaces=interfaces,
            dependencies=["jsonwebtoken", "bcryptjs"],
            signals={"events": ["user.registered", "user.authenticated"]},
        ))

    if middleware_apis:
        interfaces = {}
        for a in middleware_apis:
            if a.get("type") == "function":
                interfaces[a["name"]] = {"type": "middleware", "signature": a.get("signature", "")}

        capabilities.append(Capability(
            id=f"cap_middleware_{repo_id[:8]}",
            name="Token Verification Middleware",
            description="Express middleware for validating JWT tokens on protected routes",
            category="middleware",
            repo=repo_id,
            commit=commit,
            entry_points=[],
            interfaces=interfaces,
            dependencies=["jsonwebtoken"],
            signals={"errors": ["Unauthorized", "Forbidden"]},
        ))

    if route_apis:
        entry_points = [EntryPoint(method=a.get("method"), path=a.get("path"), file=a.get("file")) for a in route_apis]
        capabilities.append(Capability(
            id=f"cap_api_{repo_id[:8]}",
            name="HTTP API Surface",
            description="RESTful HTTP endpoints exposed by the application",
            category="api",
            repo=repo_id,
            commit=commit,
            entry_points=entry_points,
            interfaces={},
            dependencies=["express"],
            signals={},
        ))

    return capabilities


async def handle_repo_analyzed(topic: str, message: dict):
    data = message.get("data", {})
    repo_id = data.get("repo_id")
    analysis_path = data.get("analysis_path")

    if not repo_id or not analysis_path or not os.path.exists(analysis_path):
        logger.warning("Invalid repo.analyzed message", extra={"payload": message})
        return

    logger.info("Extracting capabilities", extra={"repo_id": repo_id})

    try:
        with open(analysis_path, "r") as f:
            analysis = json.load(f)

        capabilities = extract_capabilities(analysis, repo_id, analysis.get("commit", "unknown"))

        # Insert into PostgreSQL
        async with engine.begin() as conn:
            for cap in capabilities:
                await conn.execute(
                    text("""
                        INSERT INTO capabilities (id, name, description, category, repo, commit, entry_points, interfaces, dependencies, signals)
                        VALUES (:id, :name, :description, :category, :repo, :commit, :entry_points, :interfaces, :dependencies, :signals)
                        ON CONFLICT (id) DO UPDATE SET
                            name = EXCLUDED.name,
                            description = EXCLUDED.description,
                            entry_points = EXCLUDED.entry_points,
                            interfaces = EXCLUDED.interfaces,
                            dependencies = EXCLUDED.dependencies,
                            signals = EXCLUDED.signals
                    """),
                    {
                        "id": cap.id,
                        "name": cap.name,
                        "description": cap.description,
                        "category": cap.category,
                        "repo": cap.repo,
                        "commit": cap.commit,
                        "entry_points": json.dumps([ep.model_dump() for ep in cap.entry_points]),
                        "interfaces": json.dumps(cap.interfaces),
                        "dependencies": cap.dependencies,
                        "signals": json.dumps(cap.signals),
                    }
                )

        # Emit event
        for cap in capabilities:
            event = {
                "specversion": "1.0",
                "type": "capability.generated",
                "source": "capability-service",
                "id": str(uuid.uuid4()),
                "time": datetime.utcnow().isoformat() + "Z",
                "datacontenttype": "application/json",
                "data": {
                    "repo": repo_id,
                    "commit": analysis.get("commit"),
                    "capability_id": cap.id,
                    "capability_name": cap.name,
                },
            }
            await producer.send("capability.generated", event, key=cap.id)

        logger.info("Capabilities generated", extra={"repo_id": repo_id, "count": len(capabilities)})
    except Exception:
        logger.exception("Capability extraction failed", extra={"repo_id": repo_id})


producer: KafkaProducer | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global producer
    producer = KafkaProducer(settings.kafka_bootstrap_servers)
    await producer.start()

    consumer = KafkaConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        topics=["repo.analyzed"],
        group_id=f"{settings.kafka_group_id}-capability",
        handler=handle_repo_analyzed,
    )
    await consumer.start()
    task = asyncio.create_task(consumer.run())
    logger.info("Capability service started")

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await consumer.stop()
    await producer.stop()

app = FastAPI(title="Capability Service", version="1.0.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "capability"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
