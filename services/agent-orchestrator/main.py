"""Agent Orchestrator: multi-agent collaboration router with state machine."""
import os
import sys
import json
import uuid
import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from enum import Enum

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

sys.path.insert(0, "/app")
from libs.common import configure_logging, get_settings, AsyncSessionLocal
from libs.agents import AgentTask, AgentResult
from service.agents.planner import PlannerAgent
from service.agents.executor import ExecutorAgent
from service.agents.debug import DebugAgent
from service.agents.reviewer import ReviewerAgent

settings = get_settings()
logger = configure_logging(settings.app_name, settings.log_level)

QUERY_URL = os.getenv("QUERY_SERVICE_URL", "http://query-service:8080")
EXECUTION_URL = os.getenv("EXECUTION_SERVICE_URL", "http://execution-service:8080")
FEEDBACK_URL = os.getenv("FEEDBACK_SERVICE_URL", "http://feedback-service:8080")


class OrchestratorState(str, Enum):
    INIT = "init"
    PLANNING = "planning"
    EXECUTING = "executing"
    DEBUGGING = "debugging"
    REVIEWING = "reviewing"
    COMPLETE = "complete"
    FAILED = "failed"


class AgentExecuteRequest(BaseModel):
    query: str
    repo: str | None = None
    context: dict = {}
    auto_approve: bool = False
    max_agents: int = 4


class AgentExecuteResponse(BaseModel):
    execution_id: str
    agents_used: list[str]
    final_status: str
    playbook_id: str | None = None
    trace: list[dict]


class Orchestrator:
    def __init__(self):
        self.planner = PlannerAgent(QUERY_URL)
        self.executor = ExecutorAgent(EXECUTION_URL)
        self.debug = DebugAgent()
        self.reviewer = ReviewerAgent()
        self.max_debug_iterations = 2

    async def run(self, req: AgentExecuteRequest) -> AgentExecuteResponse:
        execution_id = str(uuid.uuid4())
        trace = []
        state = OrchestratorState.INIT
        agents_used = []
        playbook_id = None
        context = dict(req.context)

        logger.info("Orchestrator starting", extra={"execution_id": execution_id, "query": req.query})

        # Phase 1: Planning
        state = OrchestratorState.PLANNING
        plan_task = AgentTask(
            task_id=f"{execution_id}_plan",
            task_type="intent_parsing",
            to_agent="planner",
            payload={"query": req.query, "repo": req.repo},
        )
        plan_result = await self.planner.execute(plan_task)
        trace.append({"agent": "planner", "status": plan_result.status, "output": plan_result.output})
        agents_used.append("planner")

        if plan_result.status != "success":
            return AgentExecuteResponse(
                execution_id=execution_id,
                agents_used=agents_used,
                final_status="failed",
                trace=trace,
            )

        playbook_id = plan_result.payload.get("playbook_id")
        if not playbook_id:
            return AgentExecuteResponse(
                execution_id=execution_id,
                agents_used=agents_used,
                final_status="failed",
                trace=trace,
            )

        # Phase 2: Execution with retry loop
        state = OrchestratorState.EXECUTING
        debug_iterations = 0

        while debug_iterations <= self.max_debug_iterations:
            exec_task = AgentTask(
                task_id=f"{execution_id}_exec_{debug_iterations}",
                task_type="step_execution",
                to_agent="executor",
                payload={"playbook_id": playbook_id, "context": context},
            )
            exec_result = await self.executor.execute(exec_task)
            trace.append({"agent": "executor", "status": exec_result.status, "output": exec_result.output})
            if "executor" not in agents_used:
                agents_used.append("executor")

            if exec_result.status == "success":
                break

            # Need debug
            if debug_iterations >= self.max_debug_iterations:
                state = OrchestratorState.FAILED
                break

            state = OrchestratorState.DEBUGGING
            debug_task = AgentTask(
                task_id=f"{execution_id}_debug_{debug_iterations}",
                task_type="failure_diagnosis",
                to_agent="debug",
                payload={
                    "error_log": exec_result.output,
                    "failed_step": "execution",
                    "repo_context": context,
                },
            )
            debug_result = await self.debug.execute(debug_task)
            trace.append({"agent": "debug", "status": debug_result.status, "output": debug_result.output})
            if "debug" not in agents_used:
                agents_used.append("debug")

            # Apply debug suggestions to context
            patch = debug_result.payload
            if patch.get("auto_fixable"):
                context.update(patch.get("suggested_context_update", {}))
                context["_debug_patch_applied"] = True

            debug_iterations += 1
            state = OrchestratorState.EXECUTING

        if state == OrchestratorState.FAILED:
            return AgentExecuteResponse(
                execution_id=execution_id,
                agents_used=agents_used,
                final_status="failed",
                playbook_id=playbook_id,
                trace=trace,
            )

        # Phase 3: Review
        state = OrchestratorState.REVIEWING

        # Fetch execution details from execution service
        execution_logs = []
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                exec_id = exec_result.payload.get("execution_id")
                if exec_id:
                    resp = await client.get(f"{EXECUTION_URL}/execute/{exec_id}")
                    if resp.status_code == 200:
                        exec_data = resp.json()
                        execution_logs = exec_data.get("logs", [])
        except Exception:
            pass

        review_task = AgentTask(
            task_id=f"{execution_id}_review",
            task_type="output_verification",
            to_agent="reviewer",
            payload={
                "execution_logs": execution_logs,
                "modified_files": [],
                "steps_completed": len(execution_logs),
                "total_steps": exec_result.payload.get("total_steps", 1),
            },
        )
        review_result = await self.reviewer.execute(review_task)
        trace.append({"agent": "reviewer", "status": review_result.status, "output": review_result.output})
        if "reviewer" not in agents_used:
            agents_used.append("reviewer")

        if review_result.status == "success":
            state = OrchestratorState.COMPLETE
            final_status = "completed"
        else:
            state = OrchestratorState.FAILED
            final_status = "failed"

        # Submit feedback
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{FEEDBACK_URL}/feedback",
                    json={
                        "execution_id": execution_id,
                        "playbook_id": playbook_id,
                        "status": "success" if final_status == "completed" else "failure",
                        "execution_time_ms": 0,
                        "errors": review_result.payload.get("issues", []),
                        "agent_actions": [{"agent": t["agent"], "status": t["status"]} for t in trace],
                    }
                )
        except Exception:
            pass

        return AgentExecuteResponse(
            execution_id=execution_id,
            agents_used=agents_used,
            final_status=final_status,
            playbook_id=playbook_id,
            trace=trace,
        )


orchestrator = Orchestrator()

app = FastAPI(title="Agent Orchestrator", version="2.0.0")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent-orchestrator"}

@app.post("/agents/execute", response_model=AgentExecuteResponse)
async def agent_execute(req: AgentExecuteRequest):
    result = await orchestrator.run(req)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
