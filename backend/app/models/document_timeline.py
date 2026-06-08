"""Timeline events extracted from documents."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from app.db.database import Base


class DocumentTimeline(Base):
    __tablename__ = "document_timeline"
    __table_args__ = (UniqueConstraint("document_id", name="uq_document_timeline_document_id"),)

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    events = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list)
    model = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
