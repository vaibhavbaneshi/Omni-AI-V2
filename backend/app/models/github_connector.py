"""GitHub connector models — repo sync metadata."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from app.db.database import Base


class GitHubConnection(Base):
    __tablename__ = "github_connections"
    __table_args__ = (UniqueConstraint("user_id", name="uq_github_connections_user_id"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    github_user_id = Column(String(64), nullable=False)
    github_login = Column(String(128), nullable=False)
    access_token = Column(Text, nullable=False)
    scopes = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GitHubRepositorySync(Base):
    __tablename__ = "github_repository_syncs"
    __table_args__ = (UniqueConstraint("user_id", "repo_full_name", name="uq_github_repo_sync"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connection_id = Column(Integer, ForeignKey("github_connections.id", ondelete="CASCADE"), nullable=False)
    repo_full_name = Column(String(256), nullable=False, index=True)
    default_branch = Column(String(128), nullable=False, default="main")
    workspace_id = Column(String(64), nullable=False, default="default")
    collection_id = Column(Integer, ForeignKey("document_collections.id", ondelete="SET NULL"), nullable=True)
    last_sync_at = Column(DateTime, nullable=True)
    last_commit_sha = Column(String(64), nullable=True)
    sync_status = Column(String(32), nullable=False, default="idle")
    files_indexed = Column(Integer, nullable=False, default=0)
    sync_metadata = Column("metadata", JSON().with_variant(JSONB, "postgresql"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
