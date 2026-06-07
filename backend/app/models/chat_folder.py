"""User-defined folders for organizing chat sessions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

from app.db.database import Base


class ChatFolder(Base):
    __tablename__ = "chat_folders"
    __table_args__ = (
        UniqueConstraint("user_id", "workspace_id", "name", name="uq_chat_folders_user_workspace_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    workspace_id = Column(String, nullable=False, default="default", index=True)
    name = Column(String(120), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
