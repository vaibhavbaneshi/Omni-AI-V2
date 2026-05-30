"""Aggregate analytics from PostgreSQL usage tables and core models."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.analytics import ApiUsage, ModelUsage, TokenUsage
from app.models.chat_session import ChatSession
from app.models.document import DocumentRecord
from app.models.message import Message
from app.models.user import User


def _since(days: int) -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)


def _avg_latency(query_result) -> float:
    value = query_result or 0.0
    return round(float(value), 2)


def get_user_overview(db: Session, *, user_id: int, days: int = 30) -> dict:
    """Analytics scoped to a single user."""
    since = _since(days)

    total_messages = (
        db.query(func.count(Message.id))
        .filter(Message.user_id == user_id, Message.created_at >= since)
        .scalar()
        or 0
    )

    total_sessions = (
        db.query(func.count(ChatSession.id))
        .filter(ChatSession.user_id == user_id, ChatSession.created_at >= since)
        .scalar()
        or 0
    )

    total_tokens = (
        db.query(func.coalesce(func.sum(TokenUsage.total_tokens), 0))
        .filter(TokenUsage.user_id == user_id, TokenUsage.created_at >= since)
        .scalar()
        or 0
    )

    avg_latency = _avg_latency(
        db.query(func.avg(ModelUsage.latency_ms))
        .filter(ModelUsage.user_id == user_id, ModelUsage.created_at >= since)
        .scalar()
    )

    api_requests = (
        db.query(func.count(ApiUsage.id))
        .filter(ApiUsage.user_id == user_id, ApiUsage.created_at >= since)
        .scalar()
        or 0
    )

    uploads = (
        db.query(func.count(DocumentRecord.id))
        .filter(DocumentRecord.user_id == user_id, DocumentRecord.created_at >= since)
        .scalar()
        or 0
    )

    daily_tokens = _daily_token_series(db, user_id=user_id, days=min(days, 14))

    model_breakdown = _model_token_breakdown(db, user_id=user_id, since=since)

    return {
        "scope": "user",
        "period_days": days,
        "users": {
            "sessions": int(total_sessions),
            "messages": int(total_messages),
            "api_requests": int(api_requests),
        },
        "ai": {
            "total_tokens": int(total_tokens),
            "avg_latency_ms": avg_latency,
            "model_breakdown": model_breakdown,
            "daily_tokens": daily_tokens,
        },
        "rag": {
            "uploads": int(uploads),
            "ingestion_runs": _ingestion_count(db, user_id=user_id, since=since),
        },
    }


def get_platform_overview(db: Session, *, days: int = 30) -> dict:
    """Platform-wide analytics for admin dashboards."""
    since = _since(days)
    since_day = _since(1)

    total_users = db.query(func.count(User.id)).scalar() or 0

    active_users_day = (
        db.query(func.count(func.distinct(ApiUsage.user_id)))
        .filter(ApiUsage.created_at >= since_day, ApiUsage.user_id.isnot(None))
        .scalar()
        or 0
    )

    active_users_period = (
        db.query(func.count(func.distinct(ApiUsage.user_id)))
        .filter(ApiUsage.created_at >= since, ApiUsage.user_id.isnot(None))
        .scalar()
        or 0
    )

    total_messages = (
        db.query(func.count(Message.id)).filter(Message.created_at >= since).scalar() or 0
    )

    total_tokens = (
        db.query(func.coalesce(func.sum(TokenUsage.total_tokens), 0))
        .filter(TokenUsage.created_at >= since)
        .scalar()
        or 0
    )

    avg_latency = _avg_latency(
        db.query(func.avg(ModelUsage.latency_ms))
        .filter(ModelUsage.created_at >= since)
        .scalar()
    )

    uploads = (
        db.query(func.count(DocumentRecord.id))
        .filter(DocumentRecord.created_at >= since)
        .scalar()
        or 0
    )

    chat_requests = (
        db.query(func.count(ApiUsage.id))
        .filter(
            ApiUsage.created_at >= since,
            ApiUsage.path.in_(["/chat-stream", "/chat"]),
        )
        .scalar()
        or 0
    )

    return {
        "scope": "platform",
        "period_days": days,
        "users": {
            "total_users": int(total_users),
            "active_users_24h": int(active_users_day),
            "active_users_period": int(active_users_period),
        },
        "ai": {
            "total_chats": int(chat_requests),
            "total_messages": int(total_messages),
            "total_tokens": int(total_tokens),
            "avg_latency_ms": avg_latency,
            "model_breakdown": _model_token_breakdown(db, user_id=None, since=since),
            "daily_tokens": _daily_token_series(db, user_id=None, days=min(days, 14)),
            "endpoint_latency": _endpoint_latency(db, since=since),
        },
        "rag": {
            "uploads": int(uploads),
            "ingestion_runs": _ingestion_count(db, user_id=None, since=since),
            "total_chunks": int(
                db.query(func.coalesce(func.sum(DocumentRecord.chunks_created), 0))
                .filter(DocumentRecord.created_at >= since)
                .scalar()
                or 0
            ),
        },
    }


def _daily_token_series(
    db: Session,
    *,
    user_id: int | None,
    days: int,
) -> list[dict]:
    since = _since(days)
    query = db.query(
        func.date(TokenUsage.created_at).label("day"),
        func.coalesce(func.sum(TokenUsage.total_tokens), 0).label("tokens"),
    ).filter(TokenUsage.created_at >= since)

    if user_id is not None:
        query = query.filter(TokenUsage.user_id == user_id)

    rows = query.group_by(func.date(TokenUsage.created_at)).order_by("day").all()
    return [{"date": str(row.day), "tokens": int(row.tokens)} for row in rows]


def _model_token_breakdown(
    db: Session,
    *,
    user_id: int | None,
    since: datetime,
) -> list[dict]:
    query = db.query(
        TokenUsage.model,
        func.coalesce(func.sum(TokenUsage.total_tokens), 0).label("tokens"),
        func.count(TokenUsage.id).label("calls"),
    ).filter(TokenUsage.created_at >= since)

    if user_id is not None:
        query = query.filter(TokenUsage.user_id == user_id)

    rows = (
        query.group_by(TokenUsage.model)
        .order_by(func.sum(TokenUsage.total_tokens).desc())
        .limit(8)
        .all()
    )

    total = sum(int(row.tokens) for row in rows) or 1
    return [
        {
            "model": row.model,
            "tokens": int(row.tokens),
            "calls": int(row.calls),
            "share_pct": round(int(row.tokens) / total * 100, 1),
        }
        for row in rows
    ]


def _endpoint_latency(db: Session, *, since: datetime) -> list[dict]:
    rows = (
        db.query(
            ApiUsage.path,
            func.avg(ApiUsage.duration_ms).label("avg_ms"),
            func.count(ApiUsage.id).label("requests"),
        )
        .filter(ApiUsage.created_at >= since)
        .group_by(ApiUsage.path)
        .order_by(func.count(ApiUsage.id).desc())
        .limit(10)
        .all()
    )
    return [
        {
            "path": row.path,
            "avg_latency_ms": round(float(row.avg_ms or 0), 2),
            "requests": int(row.requests),
        }
        for row in rows
    ]


def _ingestion_count(db: Session, *, user_id: int | None, since: datetime) -> int:
    query = db.query(func.count(ModelUsage.id)).filter(
        ModelUsage.endpoint == "document.ingest",
        ModelUsage.created_at >= since,
    )
    if user_id is not None:
        query = query.filter(ModelUsage.user_id == user_id)
    return int(query.scalar() or 0)
