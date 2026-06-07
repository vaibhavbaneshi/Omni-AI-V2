"""Abuse detection helpers — prompt injection, rate-limit events, audit logging."""

from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.sanitize import detect_prompt_injection
from app.services.security_audit_service import audit_log

logger = logging.getLogger("omni.security")

_SPAM_PATTERNS = [
    re.compile(r"(.)\1{20,}"),
    re.compile(r"\b(buy now|click here|free money|crypto giveaway)\b", re.I),
]

_EXCESSIVE_SPECIAL = re.compile(r"[^\w\s]{40,}")


def detect_abuse_patterns(text: str) -> list[str]:
    """Return labels for non-injection abuse heuristics."""
    haystack = text or ""
    labels: list[str] = []
    if _EXCESSIVE_SPECIAL.search(haystack):
        labels.append("excessive_special_characters")
    for pattern in _SPAM_PATTERNS:
        if pattern.search(haystack):
            labels.append(pattern.pattern)
    return labels


def evaluate_chat_query(
    query: str,
    *,
    db: Session | None,
    user_id: int | None,
    ip_address: str | None,
    surface: str = "chat",
) -> dict[str, Any]:
    """Inspect a chat query and emit security audit events when needed."""
    injection_matches = detect_prompt_injection(query)
    abuse_matches = detect_abuse_patterns(query)

    if injection_matches:
        audit_log(
            db,
            action="prompt_injection.detected",
            user_id=user_id,
            ip_address=ip_address,
            detail={"matches": injection_matches[:5], "surface": surface},
        )

    if abuse_matches:
        audit_log(
            db,
            action="abuse.pattern.detected",
            user_id=user_id,
            ip_address=ip_address,
            detail={"matches": abuse_matches[:5], "surface": surface},
        )

    return {
        "injection_matches": injection_matches,
        "abuse_matches": abuse_matches,
        "blocked": False,
    }


def record_rate_limit_event(
    *,
    db: Session | None,
    client_ip: str,
    path: str,
    scope_name: str,
    limit: int,
    user_id: int | None = None,
) -> None:
    session = db
    owns_session = False
    if session is None:
        session = SessionLocal()
        owns_session = True

    try:
        audit_log(
            session,
            action="rate_limit.exceeded",
            user_id=user_id,
            ip_address=client_ip,
            detail={
                "path": path,
                "scope": scope_name,
                "limit": limit,
            },
        )
    finally:
        if owns_session:
            session.close()

    logger.warning(
        "rate_limit.exceeded ip=%s path=%s scope=%s limit=%s",
        client_ip,
        path,
        scope_name,
        limit,
    )
