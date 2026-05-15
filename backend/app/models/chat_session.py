from sqlalchemy import (  # type: ignore[import]
    Column,
    Integer,
    String
)

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