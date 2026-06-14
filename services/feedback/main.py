"""Feedback Service: aggregates execution logs, detects failure patterns, computes RL metrics."""
import os
import sys
import json
import uuid
import asyncio
import logging
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import Any
from collections import Counter

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, "/app")
from libs.common import configure_logging, get_settings, KafkaProducer, KafkaConsumer, AsyncSessionLocal

settings = get_settings()
logger = configure_logging(settings.app_name, settings.log_level)


class FeedbackSubmission(BaseModel):
    execution_id: str
    playbook_id: str
    status: str  # success, failure, partial
    execution_time_ms: int | None = None
    errors: list[str] = []
    agent_actions: list[dict] = []
    context: dict = {}


class PlaybookMetrics(BaseModel):
    playbook_id: str
    version: str | None = None
    success_rate: float
    avg_execution_time_ms: int
    failure_types: list[str]
    episodes: int
    score: float


def compute_score(success_rate: float, avg_time: float, baseline_time: float = 5000) -> float:
    """Compute RL score: 50% success + 20% speed + 30% stability."""
    speed = min(1.0, baseline_time / max(avg_time, 1))
    stability = 1.0 - (success_rate * (1 - success_rate) * 4)  # penalize variance
    return round(min(1.0, (success_rate * 0.50) + (speed * 0.20) + (stability * 0.30)), 3)


async def analyze_failure_patterns(feedback_rows: list[dict]) -> list[dict]:
    """Detect recurring failure patterns from feedback."""
    errors = []
    for row in feedback_rows:
        errors.extend(row.get("errors") or [])

    if not errors:
        return []

    # Simple pattern detection: group by error message similarity
    counter = Counter(errors)
    patterns = []
    for error_msg, count in counter.most_common(5):
        if count >= 2:
            patterns.append({
                "pattern_id": f"pat_{uuid.uuid4().hex[:8]}",
                "error_message": error_msg,
                "frequency": count,
                "recommended_action": infer_recommended_action(error_msg),
                "confidence": min(0.95, 0.5 + (count * 0.1)),
            })
    return patterns


def infer_recommended_action(error_msg: str) -> str:
    """Map common errors to recommended fixes."""
    msg = error_msg.lower()
    if "missing" in msg and "depend" in msg:
        return "inject_dependency_check_step"
    elif "syntax" in msg or "unexpected token" in msg:
        return "add_syntax_validation_step"
    elif "permission" in msg or "unauthorized" in msg:
        return "add_permission_precondition"
    elif "timeout" in msg or "etimedout" in msg:
        return "increase_timeout_or_add_retry"
    elif "not found" in msg or "enoent" in msg:
        return "add_file_existence_check"
    else:
        return "add_generic_error_handling"


async def process_execution_event(topic: str, message: dict):
    """Kafka handler for execution.completed events."""
    data = message.get("data", {})
    execution_id = data.get("execution_id")
    playbook_id = data.get("playbook_id")
    status = data.get("status")

    if not execution_id or not playbook_id:
        logger.warning("Invalid execution.completed message", extra={"payload": message})
        return

    logger.info("Processing execution feedback", extra={"execution_id": execution_id, "playbook_id": playbook_id})

    session: AsyncSession = AsyncSessionLocal()
    try:
        # Insert feedback record
        await session.execute(
            text("""
                INSERT INTO feedback (execution_id, playbook_id, status, execution_time_ms, errors, agent_actions, context)
                VALUES (:eid, :pbid, :status, :etime, :errors, :actions, :ctx)
            """),
            {
                "eid": execution_id,
                "pbid": playbook_id,
                "status": status,
                "etime": data.get("execution_time_ms"),
                "errors": data.get("errors", []),
                "actions": json.dumps(data.get("agent_actions", [])),
                "ctx": json.dumps(data.get("context", {})),
            }
        )
        await session.commit()

        # Aggregate metrics for this playbook
        result = await session.execute(
            text("""
                SELECT 
                    COUNT(*) as episodes,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successes,
                    AVG(execution_time_ms) as avg_time,
                    array_agg(errors) as all_errors
                FROM feedback
                WHERE playbook_id = :pbid
                AND created_at > NOW() - INTERVAL '7 days'
            """),
            {"pbid": playbook_id}
        )
        row = result.mappings().first()
        episodes = row["episodes"] or 0
        successes = row["successes"] or 0
        avg_time = row["avg_time"] or 5000
        all_errors_nested = row["all_errors"] or []

        # Flatten errors
        all_errors = []
        for item in all_errors_nested:
            if isinstance(item, list):
                all_errors.extend(item)
            elif item:
                all_errors.append(item)

        success_rate = successes / episodes if episodes > 0 else 0.0
        score = compute_score(success_rate, avg_time)

        # Detect failure patterns
        feedback_rows = [{"errors": all_errors[i:i+5]} for i in range(0, len(all_errors), 5)]
        patterns = await analyze_failure_patterns([{"errors": all_errors}])

        # Update playbook score
        await session.execute(
            text("""
                UPDATE playbooks 
                SET score = :score, episodes = :episodes
                WHERE id = :pbid
            """),
            {"score": score, "episodes": episodes, "pbid": playbook_id}
        )
        await session.commit()

        # Insert RL history
        await session.execute(
            text("""
                INSERT INTO rl_score_history (playbook_id, version, score, success_rate, avg_execution_time_ms, episodes)
                SELECT id, version, :score, :sr, :avg, :ep FROM playbooks WHERE id = :pbid
            """),
            {"score": score, "sr": success_rate, "avg": int(avg_time), "ep": episodes, "pbid": playbook_id}
        )
        await session.commit()

        # Emit feedback.analyzed event if patterns detected or low score
        if patterns or score < 0.60:
            event = {
                "specversion": "1.0",
                "type": "feedback.analyzed",
                "source": "feedback-service",
                "id": str(uuid.uuid4()),
                "time": datetime.utcnow().isoformat() + "Z",
                "datacontenttype": "application/json",
                "data": {
                    "playbook_id": playbook_id,
                    "score": score,
                    "success_rate": success_rate,
                    "episodes": episodes,
                    "patterns": patterns,
                    "avg_execution_time_ms": int(avg_time),
                },
            }
            await producer.send("feedback.analyzed", event, key=playbook_id)
            logger.info(
                "Feedback analyzed and event emitted",
                extra={"playbook_id": playbook_id, "score": score, "patterns": len(patterns)},
            )
    except Exception:
        logger.exception("Feedback processing failed", extra={"execution_id": execution_id})
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
        topics=["execution.completed"],
        group_id=f"{settings.kafka_group_id}-feedback",
        handler=process_execution_event,
    )
    await consumer.start()
    task = asyncio.create_task(consumer.run())
    logger.info("Feedback service started")

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await consumer.stop()
    await producer.stop()

app = FastAPI(title="Feedback Service", version="2.0.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "feedback"}

@app.post("/feedback", status_code=201)
async def submit_feedback(feedback: FeedbackSubmission):
    """Manual feedback submission (also used by execution service)."""
    session: AsyncSession = AsyncSessionLocal()
    try:
        await session.execute(
            text("""
                INSERT INTO feedback (execution_id, playbook_id, status, execution_time_ms, errors, agent_actions, context)
                VALUES (:eid, :pbid, :status, :etime, :errors, :actions, :ctx)
            """),
            {
                "eid": feedback.execution_id,
                "pbid": feedback.playbook_id,
                "status": feedback.status,
                "etime": feedback.execution_time_ms,
                "errors": feedback.errors,
                "actions": json.dumps(feedback.agent_actions),
                "ctx": json.dumps(feedback.context),
            }
        )
        await session.commit()
        return {"status": "recorded", "feedback_id": str(uuid.uuid4())}
    finally:
        await session.close()

@app.get("/feedback/{playbook_id}/metrics", response_model=PlaybookMetrics)
async def get_metrics(playbook_id: str):
    session: AsyncSession = AsyncSessionLocal()
    try:
        result = await session.execute(
            text("""
                SELECT 
                    p.version,
                    p.score,
                    p.episodes,
                    COALESCE(
                        (SELECT success_rate FROM rl_score_history 
                         WHERE playbook_id = p.id ORDER BY computed_at DESC LIMIT 1),
                        0.0
                    ) as success_rate,
                    COALESCE(
                        (SELECT avg_execution_time_ms FROM rl_score_history 
                         WHERE playbook_id = p.id ORDER BY computed_at DESC LIMIT 1),
                        0
                    ) as avg_time
                FROM playbooks p
                WHERE p.id = :pbid
            """),
            {"pbid": playbook_id}
        )
        row = result.mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Playbook not found")

        # Get failure types
        err_result = await session.execute(
            text("""
                SELECT errors FROM feedback 
                WHERE playbook_id = :pbid AND status != 'success'
                ORDER BY created_at DESC LIMIT 50
            """),
            {"pbid": playbook_id}
        )
        all_errors = []
        for r in err_result.mappings().all():
            e = r["errors"]
            if e:
                all_errors.extend(e if isinstance(e, list) else [e])
        failure_types = list(set(all_errors[:10]))

        return PlaybookMetrics(
            playbook_id=playbook_id,
            version=row["version"],
            success_rate=float(row["success_rate"] or 0),
            avg_execution_time_ms=int(row["avg_time"] or 0),
            failure_types=failure_types,
            episodes=row["episodes"] or 0,
            score=float(row["score"] or 0),
        )
    finally:
        await session.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
