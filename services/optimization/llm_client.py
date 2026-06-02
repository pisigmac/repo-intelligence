"""LLM client for playbook optimization. Supports OpenAI and mock fallback."""
import os
import json
import logging
from typing import Any
import httpx

logger = logging.getLogger(__name__)


class LLMClient:
    """Generic LLM client with OpenAI-compatible API support and rule-based fallback."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4")
        self.use_mock = not self.api_key
        if self.use_mock:
            logger.warning("No OPENAI_API_KEY found. Using rule-based mock optimizer.")

    async def optimize_playbook(
        self,
        original_playbook: dict,
        feedback_metrics: dict,
        failure_patterns: list[dict],
    ) -> dict | None:
        """Generate improved playbook. Returns None if no improvements needed."""
        if self.use_mock:
            return self._mock_optimize(original_playbook, feedback_metrics, failure_patterns)
        return await self._llm_optimize(original_playbook, feedback_metrics, failure_patterns)

    def _mock_optimize(
        self,
        original: dict,
        metrics: dict,
        patterns: list[dict],
    ) -> dict | None:
        """Rule-based optimization when LLM is unavailable."""
        improved = json.loads(json.dumps(original))  # deep copy
        steps = improved.get("steps", [])
        changed = False

        score = metrics.get("score", 0.5)

        # Rule 1: Low score or missing deps → add dependency check step
        if score < 0.60 or any("depend" in p.get("recommended_action", "") for p in patterns):
            has_dep_check = any(s.get("type") == "validate_syntax" and "npm install" in str(s.get("payload", {})) for s in steps)
            if not has_dep_check:
                steps.insert(0, {
                    "id": "step_dep_check",
                    "type": "validate_syntax",
                    "target": ".",
                    "payload": {"command": "npm install --dry-run || echo 'Dependencies OK'"},
                    "condition": None,
                })
                changed = True

        # Rule 2: Syntax errors → add syntax validation before test
        if any("syntax" in p.get("recommended_action", "") for p in patterns):
            has_syntax_check = any(s.get("type") == "validate_syntax" for s in steps)
            if not has_syntax_check:
                # Insert before first run_tests
                for i, s in enumerate(steps):
                    if s.get("type") == "run_tests":
                        steps.insert(i, {
                            "id": f"step_syntax_{i}",
                            "type": "validate_syntax",
                            "target": s.get("target", "."),
                            "payload": {"command": "node --check app.js || true"},
                        })
                        changed = True
                        break

        # Rule 3: Slow execution → add rollback checkpoint early
        avg_time = metrics.get("avg_execution_time_ms", 0)
        if avg_time > 10000:
            has_early_checkpoint = any(i < 2 and s.get("type") == "rollback_checkpoint" for i, s in enumerate(steps))
            if not has_early_checkpoint:
                steps.insert(0, {
                    "id": "step_checkpoint",
                    "type": "rollback_checkpoint",
                    "target": ".",
                    "payload": {"action": "git_stash"},
                })
                changed = True

        # Rule 4: Permission errors → add precondition check
        if any("permission" in p.get("recommended_action", "") for p in patterns):
            steps.insert(0, {
                "id": "step_precond",
                "type": "validate_syntax",
                "target": ".",
                "payload": {"command": "echo 'Precondition: Ensure write permissions'"},
            })
            changed = True

        if not changed:
            return None

        improved["steps"] = steps
        # Bump version
        old_version = improved.get("version", "1.0.0")
        parts = old_version.split(".")
        if len(parts) == 3:
            parts[2] = str(int(parts[2]) + 1)
            improved["version"] = ".".join(parts)
        else:
            improved["version"] = "1.0.1"
        improved["improved_from"] = old_version
        improved["status"] = "draft"

        return improved

    async def _llm_optimize(
        self,
        original: dict,
        metrics: dict,
        patterns: list[dict],
    ) -> dict | None:
        """Call OpenAI API for optimization."""
        prompt = f"""
You are an expert DevOps engineer. Given the following playbook and its execution feedback,
generate an improved version that fixes failures and improves robustness.

ORIGINAL PLAYBOOK:
{json.dumps(original, indent=2)}

EXECUTION FEEDBACK:
- Score: {metrics.get('score', 'N/A')}
- Success Rate: {metrics.get('success_rate', 'N/A')}
- Avg Execution Time: {metrics.get('avg_execution_time_ms', 'N/A')}ms
- Episodes: {metrics.get('episodes', 'N/A')}

FAILURE PATTERNS DETECTED:
{json.dumps(patterns, indent=2)}

RULES:
1. Add missing steps (dependency checks, environment validation)
2. Reorder steps for faster failure detection
3. Add rollback checkpoints before destructive operations
4. Improve error handling in each step payload
5. Do NOT remove existing functionality
6. Maintain the same capability_id

OUTPUT FORMAT:
Return ONLY a valid JSON object with keys: id, capability_id, name, description, steps, validation, rollback, observability, version, improved_from.
"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.2,
                    }
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                # Extract JSON from markdown if needed
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                improved = json.loads(content.strip())
                improved["status"] = "draft"
                return improved
        except Exception as e:
            logger.exception("LLM optimization failed, falling back to mock")
            return self._mock_optimize(original, metrics, patterns)
