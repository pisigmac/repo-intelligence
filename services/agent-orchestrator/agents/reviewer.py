"""Reviewer Agent: validates execution output for correctness and policy compliance."""
import logging
from libs.agents import BaseAgent, AgentTask, AgentResult

logger = logging.getLogger(__name__)


class ReviewerAgent(BaseAgent):
    name = "reviewer"
    capabilities = ["code_review", "security_check", "policy_validation", "output_verification"]
    confidence_threshold = 0.9
    max_retries = 1

    async def execute(self, task: AgentTask) -> AgentResult:
        execution_logs = task.payload.get("execution_logs", [])
        modified_files = task.payload.get("modified_files", [])

        logger.info("Reviewer validating output")

        issues = []

        # Check for secrets in logs
        for log in execution_logs:
            output = str(log.get("output", ""))
            if "password" in output.lower() or "secret" in output.lower() or "token" in output.lower():
                if "***" not in output:
                    issues.append("Potential secret exposure in logs")

        # Check file modifications are reasonable
        for f in modified_files:
            if ".env" in f or "secret" in f.lower():
                issues.append(f"Sensitive file modified: {f}")

        # Check all steps completed
        steps_completed = task.payload.get("steps_completed", 0)
        total_steps = task.payload.get("total_steps", 1)
        if steps_completed < total_steps:
            issues.append(f"Incomplete execution: {steps_completed}/{total_steps} steps")

        # Check tests passed
        tests_passed = any("Tests passed" in str(log.get("output", "")) for log in execution_logs)
        if not tests_passed and total_steps > 2:
            issues.append("No test success detected in logs")

        status = "success" if not issues else "failure"

        return AgentResult(
            task_id=task.task_id,
            agent=self.name,
            status=status,
            output="Validation passed" if not issues else "; ".join(issues),
            payload={
                "issues": issues,
                "tests_passed": tests_passed,
                "steps_completed": steps_completed,
            },
        )
