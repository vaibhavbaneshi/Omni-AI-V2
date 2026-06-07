"""Global workspace search across chats, documents, and insights."""

from __future__ import annotations

from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from app.models.chat_session import ChatSession
from app.models.document import DocumentRecord
from app.models.document_insight import DocumentInsight
from app.models.message import Message


def _snippet(text: str, *, max_len: int = 180) -> str:
    cleaned = (text or "").strip().replace("\n", " ")
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 1].rstrip() + "…"


def global_search(
    db: Session,
    *,
    user_id: int,
    query: str,
    workspace_id: str = "default",
    limit: int = 20,
    types: set[str] | None = None,
) -> dict:
    needle = (query or "").strip()
    if len(needle) < 2:
        return {"query": needle, "results": [], "counts": {}}

    allowed = types or {"session", "message", "document", "insight"}
    pattern = f"%{needle}%"
    per_type_limit = max(5, limit // max(len(allowed), 1))
    results: list[dict] = []
    counts: dict[str, int] = {}

    if "session" in allowed:
        sessions = (
            db.query(ChatSession)
            .filter(
                ChatSession.user_id == user_id,
                ChatSession.workspace_id == workspace_id,
                ChatSession.title.ilike(pattern),
            )
            .order_by(ChatSession.id.desc())
            .limit(per_type_limit)
            .all()
        )
        counts["session"] = len(sessions)
        results.extend(
            {
                "type": "session",
                "id": item.id,
                "title": item.title,
                "snippet": item.title,
                "session_id": item.id,
                "document_id": None,
                "collection_id": None,
                "updated_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in sessions
        )

    if "message" in allowed:
        messages = (
            db.query(Message, ChatSession.title)
            .join(ChatSession, ChatSession.id == Message.session_id)
            .filter(
                Message.user_id == user_id,
                ChatSession.workspace_id == workspace_id,
                Message.content.ilike(pattern),
            )
            .order_by(Message.id.desc())
            .limit(per_type_limit)
            .all()
        )
        counts["message"] = len(messages)
        for message, session_title in messages:
            results.append(
                {
                    "type": "message",
                    "id": message.id,
                    "title": session_title or f"Chat {message.session_id}",
                    "snippet": _snippet(message.content),
                    "session_id": message.session_id,
                    "document_id": None,
                    "collection_id": None,
                    "updated_at": message.created_at.isoformat() if message.created_at else None,
                }
            )

    if "document" in allowed:
        documents = (
            db.query(DocumentRecord)
            .filter(
                DocumentRecord.user_id == user_id,
                DocumentRecord.workspace_id == workspace_id,
                DocumentRecord.filename.ilike(pattern),
            )
            .order_by(DocumentRecord.created_at.desc())
            .limit(per_type_limit)
            .all()
        )
        counts["document"] = len(documents)
        results.extend(
            {
                "type": "document",
                "id": item.id,
                "title": item.filename,
                "snippet": item.filename,
                "session_id": item.session_id,
                "document_id": item.id,
                "collection_id": item.collection_id,
                "updated_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in documents
        )

    if "insight" in allowed:
        insights = (
            db.query(DocumentInsight, DocumentRecord.filename)
            .join(DocumentRecord, DocumentRecord.id == DocumentInsight.document_id)
            .filter(
                DocumentInsight.user_id == user_id,
                DocumentRecord.workspace_id == workspace_id,
                DocumentInsight.status == "ready",
                or_(
                    DocumentRecord.filename.ilike(pattern),
                    cast(DocumentInsight.payload, String).ilike(pattern),
                ),
            )
            .order_by(DocumentInsight.updated_at.desc())
            .limit(per_type_limit)
            .all()
        )
        counts["insight"] = len(insights)
        for insight, filename in insights:
            overview = ""
            if isinstance(insight.payload, dict):
                overview = (
                    insight.payload.get("executive_summary", {}).get("overview", "")
                    if insight.payload.get("executive_summary")
                    else ""
                )
            results.append(
                {
                    "type": "insight",
                    "id": insight.id,
                    "title": filename,
                    "snippet": _snippet(overview or filename),
                    "session_id": None,
                    "document_id": insight.document_id,
                    "collection_id": None,
                    "updated_at": insight.updated_at.isoformat() if insight.updated_at else None,
                }
            )

    return {
        "query": needle,
        "results": results[:limit],
        "counts": counts,
    }
