"""SQLAlchemy ORM models matching the init-db.sql schema."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, JSON, ARRAY, Text
from libs.common.db import Base


class RepoORM(Base):
    __tablename__ = "repos"

    id = Column(String, primary_key=True)
    url = Column(Text, nullable=False)
    branch = Column(String, nullable=False, default="main")
    commit_hash = Column(String)
    status = Column(String, nullable=False, default="pending")
    storage_path = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class CapabilityORM(Base):
    __tablename__ = "capabilities"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String)
    repo = Column(String, nullable=False)
    commit = Column(String, nullable=False)
    entry_points = Column(JSON, default=list)
    interfaces = Column(JSON, default=dict)
    dependencies = Column(ARRAY(String), default=list)
    signals = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class PlaybookORM(Base):
    __tablename__ = "playbooks"

    id = Column(String, primary_key=True)
    capability_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    steps = Column(JSON, nullable=False, default=list)
    validation = Column(JSON, default=dict)
    rollback = Column(JSON, default=dict)
    observability = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class ExecutionORM(Base):
    __tablename__ = "executions"

    id = Column(String, primary_key=True)
    playbook_id = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    steps_completed = Column(Integer, default=0)
    total_steps = Column(Integer, default=0)
    logs = Column(JSON, default=list)
    context = Column(JSON, default=dict)
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True))
