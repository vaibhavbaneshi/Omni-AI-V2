"""Conversation summary persistence with LLM summarization for long threads."""

from __future__ import annotations

from app.core.app_settings import get_settings
from app.db.session import SessionLocal
from app.models.conversation_summary import ConversationSummary
from app.models.message import Message
from app.services.summary_service import summarize_conversation


def _build_conversation_text(messages: list[Message]) -> str:
    parts: list[str] = []
    for msg in messages:
        role = (msg.role or "user").strip()
        content = (msg.content or "").strip()
        if content:
            parts.append(f"{role}: {content}")
    return "\n".join(parts)


def generate_summary(session_id: int) -> None:
    """Refresh stored summary — uses LLM when the thread exceeds configured thresholds."""
    db = SessionLocal()
    try:
        messages = (
            db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.id.asc())
            .all()
        )

        if not messages:
            return

        settings = get_settings()
        conversation_text = _build_conversation_text(messages)

        if len(messages) >= settings.CONVERSATION_SUMMARY_MIN_MESSAGES:
            summary = summarize_conversation(conversation_text)
            if not summary.strip():
                summary = conversation_text[-settings.CONVERSATION_SUMMARY_MAX_CHARS :]
        else:
            summary = conversation_text[-settings.CONVERSATION_SUMMARY_MAX_CHARS :]

        existing = (
            db.query(ConversationSummary)
            .filter(ConversationSummary.session_id == session_id)
            .first()
        )

        if existing:
            existing.summary = summary
        else:
            db.add(ConversationSummary(session_id=session_id, summary=summary))

        db.commit()
    finally:
        db.close()


def get_summary(session_id: int) -> str:
    db = SessionLocal()
    try:
        summary = (
            db.query(ConversationSummary)
            .filter(ConversationSummary.session_id == session_id)
            .first()
        )
        return summary.summary if summary and summary.summary else ""
    finally:
        db.close()
