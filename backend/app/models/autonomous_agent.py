"""Autonomous agent workspace models — Phase M."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from app.db.database import Base


class AutonomousAgent(Base):
    __tablename__ = "autonomous_agents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(String(64), nullable=False, default="default")
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    agent_type = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="active")
    config = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    schedule_kind = Column(String(32), nullable=False, default="manual")
    schedule_config = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    last_run_at = Column(DateTime, nullable=True)
    template_id = Column(Integer, ForeignKey("marketplace_templates.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("autonomous_agents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="running")
    trigger = Column(String(32), nullable=False, default="manual")
    output = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    error_message = Column(Text, nullable=True)
    tokens_used = Column(Integer, nullable=False, default=0)
    latency_ms = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)


class AgentMemoryEntry(Base):
    __tablename__ = "agent_memory_entries"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("autonomous_agents.id", ondelete="CASCADE"), nullable=False, index=True)
    execution_id = Column(Integer, ForeignKey("agent_executions.id", ondelete="SET NULL"), nullable=True)
    memory_type = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    memory_metadata = Column("metadata", JSON().with_variant(JSONB, "postgresql"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(256), nullable=False)
    body = Column(Text, nullable=True)
    category = Column(String(64), nullable=False, default="system")
    link = Column(String(512), nullable=True)
    read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
