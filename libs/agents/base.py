"""Base agent classes and protocols for multi-agent collaboration."""
from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class AgentTask(BaseModel):
    task_id: str
    task_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    from_agent: Optional[str] = None
    to_agent: str
    deadline_ms: int = 30000
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentResult(BaseModel):
    task_id: str
    agent: str
    status: str  # success, failure, partial, needs_retry
    output: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BaseAgent(ABC):
    name: str = "base"
    capabilities: list[str] = []
    confidence_threshold: float = 0.7
    max_retries: int = 1

    @abstractmethod
    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute the assigned task and return result."""
        pass

    def can_handle(self, task_type: str) -> bool:
        return task_type in self.capabilities
