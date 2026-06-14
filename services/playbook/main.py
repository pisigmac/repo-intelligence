"""Playbook Service: generates executable workflows from capabilities."""
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
from libs.common import configure_logging, get_settings, KafkaProducer, KafkaConsumer, get_db
from libs.models import Playbook, PlaybookStep, ValidationSpec, RollbackSpec, ObservabilitySpec

settings = get_settings()
logger = configure_logging(settings.app_name, settings.log_level)


def generate_playbooks(capability_id: str, cap_name: str, cap_category: str, repo_id: str) -> list[Playbook]:
    """Generate playbooks for a given capability."""
    playbooks = []

    if cap_category == "auth" or "auth" in cap_name.lower():
        playbooks.append(Playbook(
            id=f"pb_add_auth_{uuid.uuid4().hex[:8]}",
            capability_id=capability_id,
            name="Add New Authenticated Endpoint",
            description="Add a new Express route with JWT middleware protection",
            steps=[
                PlaybookStep(
                    id="step_1",
                    type="code_modification",
                    target="routes/auth.js",
                    payload={
                        "action": "append_route",
                        "template": "router.METHOD('/PATH', middleware, handler);",
                    },
                ),
                PlaybookStep(
                    id="step_2",
                    type="add_middleware",
                    target="app.js",
                    payload={
                        "action": "ensure_import",
                        "import_path": "./middleware/auth",
                    },
                ),
                PlaybookStep(
                    id="step_3",
                    type="validate_syntax",
                    target="routes/auth.js",
                    payload={"command": "node --check routes/auth.js"},
                ),
                PlaybookStep(
                    id="step_4",
                    type="run_tests",
                    target=".",
                    payload={"command": "npm test"},
                ),
                PlaybookStep(
                    id="step_5",
                    type="git_commit",
                    target=".",
                    payload={"message": "feat: add new authenticated endpoint"},
                ),
            ],
            validation=ValidationSpec(
                pre_conditions=[{"check": "file_exists", "path": "routes/auth.js"}],
                post_conditions=[{"check": "tests_pass"}],
                test_command="npm test",
            ),
            rollback=RollbackSpec(
                strategy="git_revert",
                steps=[{"action": "git_reset", "target": "HEAD~1"}],
            ),
            observability=ObservabilitySpec(
                log_level="INFO",
                metrics=["execution_time", "test_coverage"],
            ),
        ))

        playbooks.append(Playbook(
            id=f"pb_debug_auth_{uuid.uuid4().hex[:8]}",
            capability_id=capability_id,
            name="Debug Authentication Flow",
            description="Trace and debug JWT authentication issues",
            steps=[
                PlaybookStep(
                    id="step_1",
                    type="rollback_checkpoint",
                    target=".",
                    payload={"action": "git_stash"},
                ),
                PlaybookStep(
                    id="step_2",
                    type="code_modification",
                    target="middleware/auth.js",
                    payload={"action": "add_logging", "level": "debug"},
                ),
                PlaybookStep(
                    id="step_3",
                    type="run_tests",
                    target=".",
                    payload={"command": "npm test -- --verbose"},
                ),
                PlaybookStep(
                    id="step_4",
                    type="validate_syntax",
                    target="middleware/auth.js",
                    payload={"command": "node --check middleware/auth.js"},
                ),
            ],
            validation=ValidationSpec(
                pre_conditions=[{"check": "file_exists", "path": "middleware/auth.js"}],
                post_conditions=[{"check": "logs_generated"}],
            ),
            rollback=RollbackSpec(
                strategy="git_revert",
                steps=[{"action": "git_stash_pop"}],
            ),
            observability=ObservabilitySpec(
                log_level="DEBUG",
                metrics=["auth_latency", "token_validation_errors"],
            ),
        ))

    if cap_category == "middleware" or "middleware" in cap_name.lower():
        playbooks.append(Playbook(
            id=f"pb_add_middleware_{uuid.uuid4().hex[:8]}",
            capability_id=capability_id,
            name="Apply Middleware to Route",
            description="Apply existing middleware to a new or existing route",
            steps=[
                PlaybookStep(
                    id="step_1",
                    type="code_modification",
                    target="app.js",
                    payload={"action": "insert_middleware_use", "position": "before_routes"},
                ),
                PlaybookStep(
                    id="step_2",
                    type="validate_syntax",
                    target="app.js",
                    payload={"command": "node --check app.js"},
                ),
                PlaybookStep(
                    id="step_3",
                    type="run_tests",
                    target=".",
                    payload={"command": "npm test"},
                ),
            ],
            validation=ValidationSpec(
                pre_conditions=[{"check": "middleware_exists"}],
                post_conditions=[{"check": "route_protected"}],
            ),
            rollback=RollbackSpec(strategy="git_revert"),
            observability=ObservabilitySpec(),
        ))

    # Generic playbook for any capability
    playbooks.append(Playbook(
        id=f"pb_generic_{uuid.uuid4().hex[:8]}",
        capability_id=capability_id,
        name=f"Explore {cap_name}",
        description=f"Inspect and document the {cap_name} capability",
        steps=[
            PlaybookStep(
                id="step_1",
                type="validate_syntax",
                target=".",
                payload={"command": "echo 'Capability explored'"},
            ),
        ],
        validation=ValidationSpec(),
        rollback=RollbackSpec(),
        observability=ObservabilitySpec(),
    ))

    return playbooks


async def handle_capability_generated(topic: str, message: dict):
    data = message.get("data", {})
    cap_id = data.get("capability_id")
    cap_name = data.get("capability_name")
    repo_id = data.get("repo")

    if not cap_id:
        logger.warning("Invalid capability.generated message", extra={"payload": message})
        return

    logger.info("Generating playbooks", extra={"capability_id": cap_id})

    try:
        # Fetch capability details from DB
        from libs.common.db import AsyncSessionLocal
        session: AsyncSession = AsyncSessionLocal()
        try:
            result = await session.execute(
                text("SELECT category FROM capabilities WHERE id = :id"),
                {"id": cap_id}
            )
            row = result.mappings().first()
            category = row["category"] if row else "unknown"
        finally:
            await session.close()

        playbooks = generate_playbooks(cap_id, cap_name, category, repo_id)

        # Insert into DB
        async with AsyncSessionLocal() as session:
            for pb in playbooks:
                await session.execute(
                    text("""
                        INSERT INTO playbooks (id, capability_id, name, description, steps, validation, rollback, observability)
                        VALUES (:id, :capability_id, :name, :description, :steps, :validation, :rollback, :observability)
                        ON CONFLICT (id) DO UPDATE SET
                            name = EXCLUDED.name,
                            description = EXCLUDED.description,
                            steps = EXCLUDED.steps
                    """),
                    {
                        "id": pb.id,
                        "capability_id": pb.capability_id,
                        "name": pb.name,
                        "description": pb.description,
                        "steps": json.dumps([s.model_dump() for s in pb.steps]),
                        "validation": json.dumps(pb.validation.model_dump()),
                        "rollback": json.dumps(pb.rollback.model_dump()),
                        "observability": json.dumps(pb.observability.model_dump()),
                    }
                )
            await session.commit()

        # Emit events
        for pb in playbooks:
            event = {
                "specversion": "1.0",
                "type": "playbook.generated",
                "source": "playbook-service",
                "id": str(uuid.uuid4()),
                "time": datetime.utcnow().isoformat() + "Z",
                "datacontenttype": "application/json",
                "data": {
                    "repo": repo_id,
                    "capability_id": cap_id,
                    "playbook_id": pb.id,
                    "playbook_name": pb.name,
                },
            }
            await producer.send("playbook.generated", event, key=pb.id)

        logger.info("Playbooks generated", extra={"capability_id": cap_id, "count": len(playbooks)})
    except Exception:
        logger.exception("Playbook generation failed", extra={"capability_id": cap_id})


producer: KafkaProducer | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global producer
    producer = KafkaProducer(settings.kafka_bootstrap_servers)
    await producer.start()

    consumer = KafkaConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        topics=["capability.generated"],
        group_id=f"{settings.kafka_group_id}-playbook",
        handler=handle_capability_generated,
    )
    await consumer.start()
    task = asyncio.create_task(consumer.run())
    logger.info("Playbook service started")

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await consumer.stop()
    await producer.stop()

app = FastAPI(title="Playbook Service", version="1.0.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "playbook"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
