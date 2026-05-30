"""Attachment-aware orchestration helpers."""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models.document import DocumentRecord

DOCUMENT_QUERY_PATTERNS = [
    re.compile(r"\b(summarize|summary|summarise)\b.*\b(file|document|pdf|upload|attachment|attached)\b", re.I),
    re.compile(r"\b(file|document|pdf|upload|attachment|attached)\b.*\b(summarize|summary|summarise|explain|describe|overview|contents?)\b", re.I),
    re.compile(r"\bwhat('s| is) in (the |this |my )?(uploaded |attached )?(file|document|pdf)\b", re.I),
    re.compile(r"\b(this|the|my|attached|uploaded)\s+(pdf|file|document)\b", re.I),
    re.compile(r"\b(read|analyze|analyse|review)\b.*\b(the |this |my )?(uploaded |attached )?(file|document|pdf)\b", re.I),
    re.compile(r"\battached file\b", re.I),
]

MATH_EXPRESSION = re.compile(
    r"(?<![a-z])(?:\d+\s*[\+\-\*\/\^]\s*\d+|\d+\s*percent\s+of\s+\d+|calculate\s+\d+|what\s+is\s+\d+\s*[\+\-\*\/])",
    re.I,
)

NO_DOCUMENT_MESSAGE = (
    "I could not find an uploaded document attached to this session. "
    "Please upload a PDF to this chat, then ask again."
)


def is_document_query(query: str) -> bool:
    text = (query or "").strip()
    if not text:
        return False
    if any(pattern.search(text) for pattern in DOCUMENT_QUERY_PATTERNS):
        return True
    lowered = text.lower()
    document_terms = ("pdf", "document", "attached", "uploaded", "attachment", "file")
    summary_terms = ("summary", "summarize", "summarise", "overview", "explain this")
    return any(term in lowered for term in document_terms) and any(
        term in lowered for term in summary_terms
    )


def needs_calculator(query: str) -> bool:
    text = (query or "").lower()
    if is_document_query(text):
        return False
    if MATH_EXPRESSION.search(text):
        return True
    math_terms = {"calculate", "multiply", "divide", "percentage", "percent of"}
    return any(term in text for term in math_terms)


def session_has_documents(
    db: Session,
    *,
    user_id: int,
    session_id: int | None,
    workspace_id: str = "default",
) -> bool:
    if session_id is None:
        return False
    count = (
        db.query(DocumentRecord)
        .filter(
            DocumentRecord.user_id == user_id,
            DocumentRecord.workspace_id == workspace_id,
            DocumentRecord.session_id == session_id,
        )
        .count()
    )
    return count > 0


def list_session_documents(
    db: Session,
    *,
    user_id: int,
    session_id: int | None,
    workspace_id: str = "default",
) -> list[DocumentRecord]:
    if session_id is None:
        return []
    return (
        db.query(DocumentRecord)
        .filter(
            DocumentRecord.user_id == user_id,
            DocumentRecord.workspace_id == workspace_id,
            DocumentRecord.session_id == session_id,
        )
        .order_by(DocumentRecord.created_at.desc())
        .all()
    )


def count_session_documents(
    db: Session,
    *,
    user_id: int,
    session_id: int | None,
    workspace_id: str = "default",
) -> int:
    if session_id is None:
        return 0
    return (
        db.query(DocumentRecord)
        .filter(
            DocumentRecord.user_id == user_id,
            DocumentRecord.workspace_id == workspace_id,
            DocumentRecord.session_id == session_id,
        )
        .count()
    )
