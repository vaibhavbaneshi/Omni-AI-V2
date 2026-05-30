"""Analytics models for API, model, and token usage tracking.

These tables power the Phase 6 analytics dashboard and operational monitoring.
Writes are best-effort (non-fatal on failure) so Railway deployments stay stable.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class ApiUsage(Base):
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    username = Column(String, nullable=True)
    method = Column(String(16), nullable=False)
    path = Column(String(512), nullable=False, index=True)
    status_code = Column(Integer, nullable=False)
    duration_ms = Column(Float, nullable=False)
    trace_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ModelUsage(Base):
    __tablename__ = "model_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=True, index=True)
    provider = Column(String(32), nullable=False)
    model = Column(String(128), nullable=False)
    endpoint = Column(String(128), nullable=False)
    latency_ms = Column(Float, nullable=False)
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    trace_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    token_usage = relationship("TokenUsage", back_populates="model_usage", uselist=False)


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=True, index=True)
    model_usage_id = Column(Integer, ForeignKey("model_usage.id"), nullable=True, index=True)
    provider = Column(String(32), nullable=False)
    model = Column(String(128), nullable=False)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    prompt_chars = Column(Integer, nullable=False, default=0)
    completion_chars = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    model_usage = relationship("ModelUsage", back_populates="token_usage")
