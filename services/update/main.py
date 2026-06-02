"""Update Service: handles incremental updates via git diff."""
import os
import sys
import json
import asyncio
import logging
import subprocess
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI

sys.path.insert(0, "/app")
from libs.common import configure_logging, get_settings, KafkaConsumer

settings = get_settings()
logger = configure_logging(settings.app_name, settings.log_level)


async def handle_execution_completed(topic: str, message: dict):
    data = message.get("data", {})
    execution_id = data.get("execution_id")
    status = data.get("status")
    logger.info("Execution completed event received", extra={"execution_id": execution_id, "status": status})
    # In production: trigger cache invalidation, notify subscribers, update metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    consumer = KafkaConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        topics=["execution.completed"],
        group_id=f"{settings.kafka_group_id}-update",
        handler=handle_execution_completed,
    )
    await consumer.start()
    task = asyncio.create_task(consumer.run())
    logger.info("Update service started")

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await consumer.stop()

app = FastAPI(title="Update Service", version="1.0.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "update"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
