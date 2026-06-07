from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String
)

from datetime import datetime

from app.db.database import Base

class ChatSession(Base):

    __tablename__ = "chat_sessions"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    title = Column(
        String,
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    workspace_id = Column(
        String,
        nullable=False,
        default="default",
        index=True
    )

    is_pinned = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    folder_id = Column(
        Integer,
        ForeignKey("chat_folders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
