"""Named entities extracted from documents."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from app.db.database import Base


class DocumentEntity(Base):
    __tablename__ = "document_entities"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(512), nullable=False, index=True)
    entity_type = Column(String(64), nullable=False, default="unknown")
    mentions = Column(Integer, nullable=False, default=1)
    context = Column(Text, nullable=True)
    metadata_json = Column("metadata", JSON().with_variant(JSONB, "postgresql"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
