"""Session lifecycle helpers (delete, cleanup)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
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


@dataclass(frozen=True)
class _DocumentCleanupTarget:
    document_id: int
    user_id: int
    filename: str
    storage_path: str


def _detach_analytics_session(db: Session, session_id: int) -> None:
    """Best-effort analytics detach — must not abort the outer delete transaction."""
    try:
        with db.begin_nested():
            db.query(TokenUsage).filter(TokenUsage.session_id == session_id).update(
                {TokenUsage.session_id: None},
                synchronize_session=False,
            )
            db.query(ModelUsage).filter(ModelUsage.session_id == session_id).update(
                {ModelUsage.session_id: None},
                synchronize_session=False,
            )
    except SQLAlchemyError:
        logger.warning(
            "Analytics detach skipped for session_id=%s (tables may be unavailable)",
            session_id,
            exc_info=True,
        )


def _cleanup_document_externals(target: _DocumentCleanupTarget) -> None:
    """Remove stored files and vector chunks after the DB row is gone."""
    if target.storage_path and os.path.exists(target.storage_path):
        try:
            os.remove(target.storage_path)
        except OSError:
            logger.debug(
                "Could not remove upload file path=%s document_id=%s",
                target.storage_path,
                target.document_id,
                exc_info=True,
            )

    try:
        chroma_collection = get_document_collection()
        matches = chroma_collection.get(
            where={
                "$and": [
                    {"user_id": str(target.user_id)},
                    {"document_id": str(target.document_id)},
                ]
            }
        )
        ids = matches.get("ids") or []
        if ids:
            chroma_collection.delete(ids=ids)
    except Exception:
        logger.debug(
            "Chroma cleanup skipped for document_id=%s during session delete",
            target.document_id,
            exc_info=True,
        )


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

    cleanup_targets = [
        _DocumentCleanupTarget(
            document_id=document.id,
            user_id=document.user_id,
            filename=document.filename,
            storage_path=document.storage_path,
        )
        for document in db.query(DocumentRecord)
        .filter(DocumentRecord.session_id == session_id)
        .all()
    ]

    try:
        _detach_analytics_session(db, session_id)

        db.query(Message).filter(Message.session_id == session_id).delete(
            synchronize_session=False
        )
        db.query(ConversationSummary).filter(
            ConversationSummary.session_id == session_id
        ).delete(synchronize_session=False)
        db.query(DocumentRecord).filter(DocumentRecord.session_id == session_id).delete(
            synchronize_session=False
        )
        db.delete(session)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception(
            "Failed to delete chat session session_id=%s user_id=%s documents=%s",
            session_id,
            user_id,
            len(cleanup_targets),
        )
        return DeleteSessionResult.FAILED

    for target in cleanup_targets:
        _cleanup_document_externals(target)

    logger.info(
        "Chat session deleted session_id=%s user_id=%s documents=%s",
        session_id,
        user_id,
        len(cleanup_targets),
    )
    return DeleteSessionResult.DELETED
