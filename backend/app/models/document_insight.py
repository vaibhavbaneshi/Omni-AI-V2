"""Persisted document intelligence artifacts (summaries, FAQs, action items, metadata)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from app.db.database import Base


class DocumentInsight(Base):
    __tablename__ = "document_insights"
    __table_args__ = (UniqueConstraint("document_id", name="uq_document_insights_document_id"),)

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="pending")
    model = Column(String(128), nullable=True)
    error_message = Column(Text, nullable=True)
    # JSON on SQLite tests; JSONB on PostgreSQL production.
    payload = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
