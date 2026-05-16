from sqlalchemy import (
    Column,
    Integer,
    Text,
    ForeignKey
)

from app.db.database import Base


class ConversationSummary(Base):

    __tablename__ = "conversation_summaries"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    session_id = Column(
        Integer,
        ForeignKey("chat_sessions.id"),
        unique=True
    )

    summary = Column(Text)