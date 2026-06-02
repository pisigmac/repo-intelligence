"""Pydantic v2 domain models for Repo Intelligence Platform."""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class Repo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[str] = None
    url: str
    branch: str = "main"
    commit_hash: Optional[str] = None
    status: str = "pending"
    storage_path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EntryPoint(BaseModel):
    method: Optional[str] = None
    path: Optional[str] = None
    file: Optional[str] = None
    line: Optional[int] = None


class Capability(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = "unknown"
    repo: str
    commit: str
    entry_points: list[EntryPoint] = Field(default_factory=list)
    interfaces: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)
    signals: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class PlaybookStep(BaseModel):
    id: str
    type: str  # code_modification, add_middleware, run_tests, git_commit, validate_syntax, rollback_checkpoint
    target: str
    payload: dict[str, Any] = Field(default_factory=dict)
    condition: Optional[str] = None


class ValidationSpec(BaseModel):
    pre_conditions: list[dict[str, Any]] = Field(default_factory=list)
    post_conditions: list[dict[str, Any]] = Field(default_factory=list)
    test_command: Optional[str] = None


class RollbackSpec(BaseModel):
    strategy: str = "git_revert"
    steps: list[dict[str, Any]] = Field(default_factory=list)


class ObservabilitySpec(BaseModel):
    log_level: str = "INFO"
    metrics: list[str] = Field(default_factory=list)


class Playbook(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    capability_id: str
    name: str
    description: Optional[str] = None
    steps: list[PlaybookStep] = Field(default_factory=list)
    validation: ValidationSpec = Field(default_factory=ValidationSpec)
    rollback: RollbackSpec = Field(default_factory=RollbackSpec)
    observability: ObservabilitySpec = Field(default_factory=ObservabilitySpec)
    created_at: Optional[datetime] = None


class ExecutionLog(BaseModel):
    step_id: str
    status: str
    output: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Execution(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[str] = None
    playbook_id: str
    status: str = "pending"
    steps_completed: int = 0
    total_steps: int = 0
    logs: list[ExecutionLog] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class QueryResult(BaseModel):
    capabilities: list[Capability] = Field(default_factory=list)
    playbooks: list[Playbook] = Field(default_factory=list)
    confidence: float = 0.0
