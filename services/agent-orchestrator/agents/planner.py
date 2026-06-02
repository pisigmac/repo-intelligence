"""Planner Agent: selects capability and playbook based on user query."""
import logging
from typing import Any
import httpx
from libs.agents import BaseAgent, AgentTask, AgentResult

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    name = "planner"
    capabilities = ["intent_parsing", "capability_matching", "playbook_selection"]
    confidence_threshold = 0.7
    max_retries = 1

    def __init__(self, query_service_url: str):
        self.query_service_url = query_service_url

    async def execute(self, task: AgentTask) -> AgentResult:
        query = task.payload.get("query", "")
        repo = task.payload.get("repo")

        logger.info("Planner analyzing query", extra={"query": query, "repo": repo})

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self.query_service_url}/query",
                    json={"query": query, "repo": repo, "top_k": 5}
                )
                resp.raise_for_status()
                data = resp.json()

            capabilities = data.get("capabilities", [])
            playbooks = data.get("playbooks", [])
            confidence = data.get("confidence", 0.0)

            if not playbooks:
                return AgentResult(
                    task_id=task.task_id,
                    agent=self.name,
                    status="failure",
                    output="No matching playbooks found",
                    payload={"confidence": confidence},
                )

            # Select best playbook (highest score or first match)
            best_pb = max(playbooks, key=lambda p: p.get("score", 0) if isinstance(p, dict) else 0)
            if isinstance(best_pb, dict):
                pb_id = best_pb.get("id")
                pb_name = best_pb.get("name")
            else:
                pb_id = best_pb.id
                pb_name = best_pb.name

            return AgentResult(
                task_id=task.task_id,
                agent=self.name,
                status="success",
                output=f"Selected playbook: {pb_name}",
                payload={
                    "playbook_id": pb_id,
                    "playbook_name": pb_name,
                    "confidence": confidence,
                    "capabilities_found": len(capabilities),
                },
            )
        except Exception as e:
            logger.exception("Planner failed")
            return AgentResult(
                task_id=task.task_id,
                agent=self.name,
                status="failure",
                output=str(e),
            )
