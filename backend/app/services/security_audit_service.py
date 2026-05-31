"""Structured security audit logging."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.user_settings import SecurityAuditLog

logger = logging.getLogger("omni.security")


SENSITIVE_KEYS = {"token", "access_token", "refresh_token", "password", "secret", "api_key"}


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[redacted]" if key.lower() in SENSITIVE_KEYS else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def audit_log(
    db: Session | None,
    *,
    action: str,
    user_id: int | None = None,
    ip_address: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    safe_detail = _redact(detail or {})
    logger.info(
        "security.audit action=%s user_id=%s ip=%s detail=%s",
        action,
        user_id,
        ip_address,
        safe_detail,
    )

    if db is None:
        return

    try:
        db.add(
            SecurityAuditLog(
                user_id=user_id,
                ip_address=ip_address,
                action=action,
                detail=json.dumps(safe_detail, sort_keys=True)[:4000],
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to persist security audit log action=%s", action)
