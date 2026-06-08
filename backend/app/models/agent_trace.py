"""Persisted multi-agent execution traces."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from app.db.database import Base


class AgentTrace(Base):
    __tablename__ = "agent_traces"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    query = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="running")
    planner_output = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    agent_steps = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    critic_output = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    final_response_preview = Column(Text, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
