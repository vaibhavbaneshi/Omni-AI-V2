"""Persist API and LLM usage metrics to PostgreSQL.

All record_* functions swallow DB errors so observability never breaks chat or uploads.
"""

from __future__ import annotations

import logging
from typing import Any

from jose import JWTError, jwt

from app.core.app_settings import get_settings
from app.core.telemetry import LLMCallMetrics, get_trace_id
from app.db.session import SessionLocal
from app.models.analytics import ApiUsage, ModelUsage, TokenUsage
from app.models.user import User
from app.services.auth_service import get_jwt_algorithm, get_jwt_secret

logger = logging.getLogger("omni.usage")


def _tracking_enabled() -> bool:
    return get_settings().ENABLE_USAGE_TRACKING


def _resolve_user_from_auth(authorization: str | None) -> tuple[int | None, str | None]:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None, None

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None, None

    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[get_jwt_algorithm()])
        username = payload.get("sub")
        if not username:
            return None, None
    except JWTError:
        return None, None

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user:
            return user.id, username
        return None, username
    finally:
        db.close()


def record_api_usage(
    *,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    authorization: str | None = None,
    trace_id: str | None = None,
) -> None:
    if not _tracking_enabled():
        return

    user_id, username = _resolve_user_from_auth(authorization)
    db = SessionLocal()
    try:
        db.add(
            ApiUsage(
                user_id=user_id,
                username=username,
                method=method,
                path=path[:512],
                status_code=status_code,
                duration_ms=round(duration_ms, 2),
                trace_id=trace_id or get_trace_id(),
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.debug("Failed to record api_usage for %s %s", method, path, exc_info=True)
    finally:
        db.close()


def record_llm_usage(
    metrics: LLMCallMetrics,
    *,
    user_id: int | None = None,
    session_id: int | None = None,
) -> None:
    if not _tracking_enabled():
        return

    db = SessionLocal()
    try:
        model_row = ModelUsage(
            user_id=user_id,
            session_id=session_id,
            provider=metrics.provider,
            model=metrics.model,
            endpoint=metrics.endpoint,
            latency_ms=round(metrics.latency_ms, 2),
            success=metrics.success,
            error_message=metrics.error_message,
            trace_id=metrics.trace_id or get_trace_id(),
        )
        db.add(model_row)
        db.flush()

        db.add(
            TokenUsage(
                user_id=user_id,
                session_id=session_id,
                model_usage_id=model_row.id,
                provider=metrics.provider,
                model=metrics.model,
                prompt_tokens=metrics.prompt_tokens,
                completion_tokens=metrics.completion_tokens,
                total_tokens=metrics.total_tokens,
                prompt_chars=metrics.prompt_chars,
                completion_chars=metrics.completion_chars,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.debug("Failed to record model/token usage", exc_info=True)
    finally:
        db.close()


def record_ingestion_event(
    *,
    user_id: int,
    filename: str,
    chunks_created: int,
    duration_ms: float,
    success: bool,
    error_message: str | None = None,
) -> None:
    """Log document ingestion as a synthetic model_usage row for RAG pipeline visibility."""
    if not _tracking_enabled():
        return

    metrics = LLMCallMetrics(
        provider="ingestion",
        model="document-pipeline",
        endpoint="document.ingest",
        prompt_chars=len(filename),
        completion_chars=chunks_created,
        prompt_tokens=None,
        completion_tokens=chunks_created,
        total_tokens=chunks_created,
        latency_ms=duration_ms,
        success=success,
        error_message=error_message,
    )
    record_llm_usage(metrics, user_id=user_id)
