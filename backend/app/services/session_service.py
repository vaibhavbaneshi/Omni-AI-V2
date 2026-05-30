"""Session lifecycle helpers (delete, cleanup)."""

from __future__ import annotations

import os

from sqlalchemy.orm import Session

from app.models.chat_session import ChatSession
from app.models.conversation_summary import ConversationSummary
from app.models.document import DocumentRecord
from app.models.message import Message
from app.services.documents_services import collection as chroma_collection


def delete_chat_session(
    db: Session,
    *,
    user_id: int,
    session_id: int,
) -> bool:
    """Delete a chat session and all owned messages, summaries, and session documents."""
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        )
        .first()
    )
    if not session:
        return False

    documents = (
        db.query(DocumentRecord)
        .filter(
            DocumentRecord.user_id == user_id,
            DocumentRecord.session_id == session_id,
        )
        .all()
    )

    for document in documents:
        if os.path.exists(document.storage_path):
            try:
                os.remove(document.storage_path)
            except OSError:
                pass

        try:
            matches = chroma_collection.get(
                where={
                    "$and": [
                        {"user_id": str(user_id)},
                        {"document_id": str(document.id)},
                    ]
                }
            )
            ids = matches.get("ids") or []
            if ids:
                chroma_collection.delete(ids=ids)
        except Exception:
            pass

        db.delete(document)

    db.query(Message).filter(
        Message.session_id == session_id,
        Message.user_id == user_id,
    ).delete(synchronize_session=False)

    db.query(ConversationSummary).filter(
        ConversationSummary.session_id == session_id
    ).delete(synchronize_session=False)

    db.delete(session)
    db.commit()
    return True
