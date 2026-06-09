"""Enterprise connector hub models — Phase N."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from app.db.database import Base


class ConnectorConnection(Base):
    __tablename__ = "connector_connections"
    __table_args__ = (UniqueConstraint("user_id", "connector_type", name="uq_connector_connections_user_type"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connector_type = Column(String(64), nullable=False)
    display_name = Column(String(256), nullable=True)
    credentials_encrypted = Column(Text, nullable=False)
    connection_metadata = Column("metadata", JSON().with_variant(JSONB, "postgresql"), nullable=True)
    status = Column(String(32), nullable=False, default="connected")
    last_sync_at = Column(DateTime, nullable=True)
    document_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConnectorSyncRun(Base):
    __tablename__ = "connector_sync_runs"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("connector_connections.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="running")
    files_synced = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    sync_metadata = Column("sync_metadata", JSON().with_variant(JSONB, "postgresql"), nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
