"""Session lifecycle helpers (delete, cleanup)."""

from __future__ import annotations

import logging
import os
from enum import Enum

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.analytics import ModelUsage, TokenUsage
from app.models.chat_session import ChatSession
from app.models.conversation_summary import ConversationSummary
from app.models.document import DocumentRecord
from app.models.message import Message
from app.services.documents_services import get_document_collection

logger = logging.getLogger(__name__)


class DeleteSessionResult(str, Enum):
    NOT_FOUND = "not_found"
    DELETED = "deleted"
    FAILED = "failed"


def delete_chat_session(
    db: Session,
    *,
    user_id: int,
    session_id: int,
) -> DeleteSessionResult:
    """Delete a chat session and all related messages, summaries, and documents."""
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        )
        .first()
    )
    if not session:
        logger.info(
            "Chat session delete skipped — not found session_id=%s user_id=%s",
            session_id,
            user_id,
        )
        return DeleteSessionResult.NOT_FOUND

    documents = (
        db.query(DocumentRecord)
        .filter(DocumentRecord.session_id == session_id)
        .all()
    )

    for document in documents:
        if os.path.exists(document.storage_path):
            try:
                os.remove(document.storage_path)
            except OSError:
                pass

        try:
            chroma_collection = get_document_collection()
            matches = chroma_collection.get(
                where={
                    "$and": [
                        {"user_id": str(document.user_id)},
                        {"document_id": str(document.id)},
                    ]
                }
            )
            ids = matches.get("ids") or []
            if ids:
                chroma_collection.delete(ids=ids)
        except Exception:
            logger.debug(
                "Chroma cleanup skipped for document_id=%s during session delete",
                document.id,
                exc_info=True,
            )

        db.delete(document)

    db.query(Message).filter(Message.session_id == session_id).delete(
        synchronize_session=False
    )

    db.query(ConversationSummary).filter(
        ConversationSummary.session_id == session_id
    ).delete(synchronize_session=False)

    # Analytics rows reference chat_sessions; detach instead of blocking delete.
    db.query(TokenUsage).filter(TokenUsage.session_id == session_id).update(
        {TokenUsage.session_id: None},
        synchronize_session=False,
    )
    db.query(ModelUsage).filter(ModelUsage.session_id == session_id).update(
        {ModelUsage.session_id: None},
        synchronize_session=False,
    )

    db.delete(session)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception(
            "Failed to delete chat session session_id=%s user_id=%s",
            session_id,
            user_id,
        )
        return DeleteSessionResult.FAILED

    logger.info(
        "Chat session deleted session_id=%s user_id=%s documents=%s",
        session_id,
        user_id,
        len(documents),
    )
    return DeleteSessionResult.DELETED
