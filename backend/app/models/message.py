from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime
)

from datetime import datetime

from app.db.database import Base


class Message(Base):

    __tablename__ = "messages"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    session_id = Column(
        Integer,
        ForeignKey("chat_sessions.id")
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        index=True
    )

    role = Column(String)

    content = Column(String)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
