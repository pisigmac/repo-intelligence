"""Execution Service: executes playbook steps, modifies code, runs tests. Phase 2: emits telemetry."""
import os
import sys
import json
import uuid
import subprocess
import shutil
import logging
import time
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, "/app")
from libs.common import configure_logging, get_settings, KafkaProducer, AsyncSessionLocal
from libs.models.orm import ExecutionORM, PlaybookORM
from libs.models import ExecutionLog

settings = get_settings()
logger = configure_logging(settings.app_name, settings.log_level)


class ExecuteRequest(BaseModel):
    playbook_id: str
    context: dict = {}


class StepExecutor:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.backup_path = repo_path + ".backup"

    def create_backup(self):
        if os.path.exists(self.backup_path):
            shutil.rmtree(self.backup_path)
        shutil.copytree(self.repo_path, self.backup_path)

    def restore_backup(self):
        if os.path.exists(self.backup_path):
            shutil.rmtree(self.repo_path)
            shutil.copytree(self.backup_path, self.repo_path)

    def execute_step(self, step: dict, context: dict) -> tuple[str, str]:
        step_type = step["type"]
        target = step["target"]
        payload = step.get("payload", {})

        target_path = os.path.join(self.repo_path, target) if not os.path.isabs(target) else target

        if step_type == "code_modification":
            return self._handle_code_modification(target_path, payload, context)
        elif step_type == "add_middleware":
            return self._handle_add_middleware(target_path, payload, context)
        elif step_type == "run_tests":
            return self._handle_run_tests(target_path, payload)
        elif step_type == "validate_syntax":
            return self._handle_validate_syntax(target_path, payload)
        elif step_type == "git_commit":
            return self._handle_git_commit(target_path, payload)
        elif step_type == "rollback_checkpoint":
            return self._handle_checkpoint(target_path, payload)
        else:
            return "skipped", f"Unknown step type: {step_type}"

    def _handle_code_modification(self, target_path: str, payload: dict, context: dict) -> tuple[str, str]:
        action = payload.get("action", "append")
        if action == "append_route":
            method = context.get("method", "get").lower()
            path = context.get("new_route", "/api/new")
            handler = context.get("handler", "(req, res) => res.json({ok: true})")
            code = f"\nrouter.{method}(\'{path}\', verifyToken, {handler});\n"
            with open(target_path, "a") as f:
                f.write(code)
            return "completed", f"Appended route {method.upper()} {path}"
        elif action == "add_logging":
            level = payload.get("level", "debug")
            log_line = f"\nconsole.{level}(\'Debug: auth middleware executed\');\n"
            with open(target_path, "a") as f:
                f.write(log_line)
            return "completed", f"Added {level} logging"
        return "skipped", "No matching action"

    def _handle_add_middleware(self, target_path: str, payload: dict, context: dict) -> tuple[str, str]:
        import_path = payload.get("import_path", "./middleware/auth")
        var_name = import_path.split("/")[-1].replace("-", "_")
        with open(target_path, "r") as f:
            content = f.read()
        import_line = f"const {var_name} = require(\'{import_path}\');\n"
        if import_line.strip() not in content:
            lines = content.splitlines()
            last_require = -1
            for i, line in enumerate(lines):
                if "require(" in line:
                    last_require = i
            lines.insert(last_require + 1, import_line.strip())
            with open(target_path, "w") as f:
                f.write("\n".join(lines))
            return "completed", f"Added middleware import"
        return "skipped", "Import already exists"

    def _handle_run_tests(self, target_path: str, payload: dict) -> tuple[str, str]:
        cmd = payload.get("command", "npm test")
        cwd = target_path if os.path.isdir(target_path) else os.path.dirname(target_path)
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=120)
        output = result.stdout + "\n" + result.stderr
        if result.returncode == 0:
            return "completed", f"Tests passed\n{output[:500]}"
        return "failed", f"Tests failed\n{output[:1000]}"

    def _handle_validate_syntax(self, target_path: str, payload: dict) -> tuple[str, str]:
        cmd = payload.get("command", f"node --check {target_path}")
        cwd = os.path.dirname(target_path) if os.path.isfile(target_path) else target_path
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return "completed", "Syntax valid"
        return "failed", f"Syntax error: {result.stderr[:500]}"

    def _handle_git_commit(self, target_path: str, payload: dict) -> tuple[str, str]:
        msg = payload.get("message", "automated commit")
        cwd = target_path if os.path.isdir(target_path) else os.path.dirname(target_path)
        subprocess.run(["git", "add", "."], cwd=cwd, capture_output=True)
        result = subprocess.run(["git", "commit", "-m", msg], cwd=cwd, capture_output=True, text=True)
        if result.returncode == 0 or "nothing to commit" in result.stdout.lower():
            return "completed", f"Committed: {msg}"
        return "failed", f"Git commit failed"

    def _handle_checkpoint(self, target_path: str, payload: dict) -> tuple[str, str]:
        action = payload.get("action", "git_stash")
        cwd = target_path if os.path.isdir(target_path) else os.path.dirname(target_path)
        if action == "git_stash":
            subprocess.run(["git", "stash", "push", "-m", "auto-checkpoint"], cwd=cwd, capture_output=True)
            return "completed", "Checkpoint created"
        elif action == "git_stash_pop":
            subprocess.run(["git", "stash", "pop"], cwd=cwd, capture_output=True)
            return "completed", "Checkpoint restored"
        return "skipped", "Unknown checkpoint action"


async def run_execution(execution_id: str, playbook_id: str, context: dict):
    start_time = time.time()
    session: AsyncSession = AsyncSessionLocal()
    try:
        result = await session.execute(
            select(PlaybookORM).where(PlaybookORM.id == playbook_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            logger.error("Playbook not found", extra={"playbook_id": playbook_id})
            return

        steps = json.loads(row.steps) if row.steps else []

        exec_row = await session.execute(
            select(ExecutionORM).where(ExecutionORM.id == execution_id)
        )
        execution = exec_row.scalar_one()
        execution.status = "running"
        execution.total_steps = len(steps)
        await session.commit()

        repo_path = context.get("repo_path", settings.repo_storage_path)
        if not os.path.exists(os.path.join(repo_path, "package.json")):
            for item in os.listdir(repo_path):
                candidate = os.path.join(repo_path, item)
                if os.path.isdir(candidate) and os.path.exists(os.path.join(candidate, "package.json")):
                    repo_path = candidate
                    break

        executor = StepExecutor(repo_path)
        executor.create_backup()

        logs = []
        steps_completed = 0
        final_status = "completed"

        for i, step in enumerate(steps):
            step_id = step.get("id", f"step_{i}")
            logger.info("Executing step", extra={"execution_id": execution_id, "step": step_id})
            try:
                status, output = executor.execute_step(step, context)
            except Exception as e:
                status = "failed"
                output = str(e)
                logger.exception("Step execution failed")

            log = ExecutionLog(step_id=step_id, status=status, output=output)
            logs.append(log.model_dump())
            steps_completed += 1

            execution.steps_completed = steps_completed
            execution.logs = logs
            await session.commit()

            if status == "failed":
                final_status = "failed"
                rollback = json.loads(row.rollback) if row.rollback else {}
                if rollback.get("strategy") == "git_revert":
                    executor.restore_backup()
                    final_status = "rolled_back"
                    logs.append(ExecutionLog(
                        step_id="rollback",
                        status="completed",
                        output="Rollback executed"
                    ).model_dump())
                    execution.logs = logs
                    execution.rollback_triggered = True
                    await session.commit()
                break

        execution_time_ms = int((time.time() - start_time) * 1000)
        execution.status = final_status
        execution.execution_time_ms = execution_time_ms
        execution.completed_at = datetime.utcnow()
        await session.commit()

        # Phase 2: Emit execution.completed event
        await emit_execution_completed(execution_id, playbook_id, final_status, logs, execution_time_ms)

        logger.info("Execution finished", extra={"execution_id": execution_id, "status": final_status})
    except Exception:
        logger.exception("Execution task failed")
    finally:
        await session.close()


# Phase 2: Kafka producer for telemetry
_phase2_producer: KafkaProducer | None = None

async def emit_execution_completed(execution_id: str, playbook_id: str, status: str, logs: list, execution_time_ms: int = 0):
    try:
        if _phase2_producer is None:
            return
        event = {
            "specversion": "1.0",
            "type": "execution.completed",
            "source": "execution-service",
            "id": execution_id,
            "time": datetime.utcnow().isoformat() + "Z",
            "datacontenttype": "application/json",
            "data": {
                "execution_id": execution_id,
                "playbook_id": playbook_id,
                "status": status,
                "execution_time_ms": execution_time_ms,
                "errors": [log.get("output", "") for log in logs if log.get("status") == "failed"],
                "agent_actions": [],
                "context": {},
            },
        }
        await _phase2_producer.send("execution.completed", event, key=playbook_id)
    except Exception:
        logger.exception("Failed to emit execution.completed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _phase2_producer
    _phase2_producer = KafkaProducer(settings.kafka_bootstrap_servers)
    await _phase2_producer.start()
    logger.info("Execution service started (Phase 2)")
    yield
    if _phase2_producer:
        await _phase2_producer.stop()

app = FastAPI(title="Execution Service", version="2.0.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "execution"}

@app.post("/execute")
async def execute_playbook(req: ExecuteRequest, background: BackgroundTasks):
    execution_id = str(uuid.uuid4())
    session = AsyncSessionLocal()
    try:
        execution = ExecutionORM(
            id=execution_id,
            playbook_id=req.playbook_id,
            status="pending",
            context=req.context,
            started_at=datetime.utcnow(),
        )
        session.add(execution)
        await session.commit()
    finally:
        await session.close()

    background.add_task(run_execution, execution_id, req.playbook_id, req.context)
    return {"execution_id": execution_id, "status": "pending", "playbook_id": req.playbook_id}

@app.get("/execute/{execution_id}")
async def get_execution(execution_id: str):
    session = AsyncSessionLocal()
    try:
        result = await session.execute(
            text("SELECT * FROM executions WHERE id = :id"),
            {"id": execution_id}
        )
        row = result.mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Execution not found")
        return dict(row)
    finally:
        await session.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
