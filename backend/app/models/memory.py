from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text
)

from app.db.database import Base


class UserMemory(Base):

    __tablename__ = "user_memories"

    id = Column(
        Integer,
        primary_key=True,
        index=True
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

    category = Column(
        String,
        nullable=False,
        default="preference"
    )

    content = Column(
        Text,
        nullable=False
    )

    importance = Column(
        Float,
        nullable=False,
        default=0.5
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
