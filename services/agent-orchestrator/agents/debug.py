"""Debug Agent: analyzes execution failures and suggests fixes."""
import logging
from typing import Any
from libs.agents import BaseAgent, AgentTask, AgentResult

logger = logging.getLogger(__name__)


class DebugAgent(BaseAgent):
    name = "debug"
    capabilities = ["failure_diagnosis", "root_cause_analysis", "patch_generation"]
    confidence_threshold = 0.6
    max_retries = 3

    async def execute(self, task: AgentTask) -> AgentResult:
        error_log = task.payload.get("error_log", "")
        failed_step = task.payload.get("failed_step", "")
        repo_context = task.payload.get("repo_context", {})

        logger.info("Debug agent analyzing failure", extra={"step": failed_step})

        # Simple rule-based diagnosis
        diagnosis = []
        fixes = []

        error_lower = error_log.lower()

        if "syntax" in error_lower or "unexpected token" in error_lower:
            diagnosis.append("Syntax error in modified code")
            fixes.append("Add syntax validation step before test execution")
            fixes.append("Use AST parser to validate JavaScript before writing")

        if "missing" in error_lower and "module" in error_lower:
            diagnosis.append("Missing npm dependency")
            fixes.append("Run npm install before executing tests")
            fixes.append("Add package.json dependency check step")

        if "permission" in error_lower or "eacces" in error_lower:
            diagnosis.append("File permission denied")
            fixes.append("Check file permissions before code modification")

        if "timeout" in error_lower or "etimedout" in error_lower:
            diagnosis.append("Test or command timed out")
            fixes.append("Increase timeout or break into smaller steps")

        if "not found" in error_lower or "enoent" in error_lower:
            diagnosis.append("Required file not found")
            fixes.append("Add file existence check as precondition")

        if not diagnosis:
            diagnosis.append("Unknown failure pattern")
            fixes.append("Review execution logs manually")
            fixes.append("Add verbose logging to failed step")

        patch = {
            "diagnosis": diagnosis,
            "recommended_fixes": fixes,
            "auto_fixable": len(fixes) > 0 and "syntax" in error_lower,
            "suggested_context_update": {
                "add_validation": True,
                "verbose_mode": True,
            }
        }

        return AgentResult(
            task_id=task.task_id,
            agent=self.name,
            status="success",
            output="; ".join(diagnosis),
            payload=patch,
        )
