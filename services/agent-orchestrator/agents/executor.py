"""Executor Agent: runs playbook via execution service."""
import logging
import httpx
from libs.agents import BaseAgent, AgentTask, AgentResult

logger = logging.getLogger(__name__)


class ExecutorAgent(BaseAgent):
    name = "executor"
    capabilities = ["step_execution", "playbook_runner"]
    confidence_threshold = 0.8
    max_retries = 2

    def __init__(self, execution_service_url: str):
        self.execution_service_url = execution_service_url

    async def execute(self, task: AgentTask) -> AgentResult:
        playbook_id = task.payload.get("playbook_id")
        context = task.payload.get("context", {})

        if not playbook_id:
            return AgentResult(
                task_id=task.task_id,
                agent=self.name,
                status="failure",
                output="Missing playbook_id",
            )

        logger.info("Executor running playbook", extra={"playbook_id": playbook_id})

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.execution_service_url}/execute",
                    json={"playbook_id": playbook_id, "context": context}
                )
                resp.raise_for_status()
                data = resp.json()

            execution_id = data.get("execution_id")
            status = data.get("status", "pending")

            return AgentResult(
                task_id=task.task_id,
                agent=self.name,
                status="success" if status != "failed" else "failure",
                output=f"Execution {status}: {execution_id}",
                payload={
                    "execution_id": execution_id,
                    "playbook_id": playbook_id,
                    "status": status,
                },
            )
        except Exception as e:
            logger.exception("Executor failed")
            return AgentResult(
                task_id=task.task_id,
                agent=self.name,
                status="failure",
                output=str(e),
            )
