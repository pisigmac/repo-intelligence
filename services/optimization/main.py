"""Optimization Service: analyzes feedback, generates improved playbooks via LLM."""
import os
import sys
import json
import uuid
import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, "/app")
from libs.common import configure_logging, get_settings, KafkaProducer, KafkaConsumer, AsyncSessionLocal
from service.llm_client import LLMClient

settings = get_settings()
logger = configure_logging(settings.app_name, settings.log_level)


async def handle_feedback_analyzed(topic: str, message: dict):
    """Kafka handler for feedback.analyzed events."""
    data = message.get("data", {})
    playbook_id = data.get("playbook_id")
    score = data.get("score", 1.0)
    patterns = data.get("patterns", [])

    if not playbook_id:
        return

    # Only optimize if score is low or patterns detected
    if score >= 0.75 and not patterns:
        logger.info("Playbook score healthy, skipping optimization", extra={"playbook_id": playbook_id, "score": score})
        return

    logger.info("Optimizing playbook", extra={"playbook_id": playbook_id, "score": score, "patterns": len(patterns)})

    session: AsyncSession = AsyncSessionLocal()
    try:
        # Fetch original playbook
        result = await session.execute(
            text("SELECT * FROM playbooks WHERE id = :pbid AND status = 'approved' ORDER BY version DESC LIMIT 1"),
            {"pbid": playbook_id}
        )
        row = result.mappings().first()
        if not row:
            logger.warning("Original playbook not found or not approved", extra={"playbook_id": playbook_id})
            return

        original = {
            "id": row["id"],
            "capability_id": row["capability_id"],
            "name": row["name"],
            "description": row["description"],
            "steps": json.loads(row["steps"]) if row["steps"] else [],
            "validation": json.loads(row["validation"]) if row["validation"] else {},
            "rollback": json.loads(row["rollback"]) if row["rollback"] else {},
            "observability": json.loads(row["observability"]) if row["observability"] else {},
            "version": row.get("version", "1.0.0"),
        }

        # Call LLM optimizer
        llm = LLMClient()
        improved = await llm.optimize_playbook(
            original,
            metrics={
                "score": score,
                "success_rate": data.get("success_rate", 0),
                "avg_execution_time_ms": data.get("avg_execution_time_ms", 0),
                "episodes": data.get("episodes", 0),
            },
            failure_patterns=patterns,
        )

        if not improved:
            logger.info("No improvements generated", extra={"playbook_id": playbook_id})
            return

        # Generate new playbook ID
        new_playbook_id = f"{playbook_id}_v{improved['version'].replace('.', '_')}"
        improved["id"] = new_playbook_id
        improved["parent_id"] = playbook_id

        # Insert as draft
        await session.execute(
            text("""
                INSERT INTO playbooks (id, capability_id, name, description, steps, validation, rollback, observability, version, parent_id, improved_from, status, score, episodes)
                VALUES (:id, :cid, :name, :desc, :steps, :val, :roll, :obs, :ver, :pid, :impfrom, 'draft', 0.0, 0)
            """),
            {
                "id": new_playbook_id,
                "cid": improved["capability_id"],
                "name": improved["name"],
                "desc": improved.get("description", ""),
                "steps": json.dumps(improved["steps"]),
                "val": json.dumps(improved.get("validation", {})),
                "roll": json.dumps(improved.get("rollback", {})),
                "obs": json.dumps(improved.get("observability", {})),
                "ver": improved["version"],
                "pid": playbook_id,
                "impfrom": improved.get("improved_from", "1.0.0"),
            }
        )
        await session.commit()

        # Create approval request
        await session.execute(
            text("""
                INSERT INTO approvals (playbook_id, version, original_playbook_id, status, changes_summary, estimated_score_improvement, requested_by)
                VALUES (:pbid, :ver, :orig, 'pending', :changes, :est_score, 'optimization-service')
            """),
            {
                "pbid": new_playbook_id,
                "ver": improved["version"],
                "orig": playbook_id,
                "changes": json.dumps({
                    "patterns_addressed": [p["pattern_id"] for p in patterns],
                    "added_steps": [s["id"] for s in improved["steps"] if s["id"] not in [os["id"] for os in original["steps"]]],
                    "reason": "Auto-improvement based on feedback analysis",
                }),
                "est_score": min(0.95, score + 0.15),
            }
        )
        await session.commit()

        # Emit event
        event = {
            "specversion": "1.0",
            "type": "playbook.improved",
            "source": "optimization-service",
            "id": str(uuid.uuid4()),
            "time": datetime.utcnow().isoformat() + "Z",
            "datacontenttype": "application/json",
            "data": {
                "original_playbook_id": playbook_id,
                "improved_playbook_id": new_playbook_id,
                "version": improved["version"],
                "improved_from": improved.get("improved_from", "1.0.0"),
                "changes": improved["steps"],
                "estimated_score_improvement": min(0.95, score + 0.15),
                "requires_approval": True,
            },
        }
        await producer.send("playbook.improved", event, key=new_playbook_id)
        logger.info("Playbook improved and queued for approval", extra={"new_id": new_playbook_id})
    except Exception:
        logger.exception("Optimization failed", extra={"playbook_id": playbook_id})
    finally:
        await session.close()


producer: KafkaProducer | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global producer
    producer = KafkaProducer(settings.kafka_bootstrap_servers)
    await producer.start()

    consumer = KafkaConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        topics=["feedback.analyzed"],
        group_id=f"{settings.kafka_group_id}-optimization",
        handler=handle_feedback_analyzed,
    )
    await consumer.start()
    task = asyncio.create_task(consumer.run())
    logger.info("Optimization service started")

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await consumer.stop()
    await producer.stop()

app = FastAPI(title="Optimization Service", version="2.0.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "optimization"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
