"""Input sanitization and prompt-injection mitigation helpers."""

from __future__ import annotations

import re

_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.I),
    re.compile(r"disregard\s+(the\s+)?(system|above)", re.I),
    re.compile(r"you\s+are\s+now\s+", re.I),
    re.compile(r"reveal\s+(the\s+)?(system\s+)?prompt", re.I),
]


def sanitize_user_query(text: str, *, max_length: int = 12_000) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    for pattern in _INJECTION_PATTERNS:
        cleaned = pattern.sub("[filtered]", cleaned)

    return cleaned


def sanitize_retrieved_context(chunks: list[str], *, max_chunks: int = 12, max_chars: int = 16_000) -> str:
    """Limit and strip control characters from retrieved context."""
    selected = chunks[:max_chunks]
    combined = "\n\n".join(selected)
    combined = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", combined)
    if len(combined) > max_chars:
        combined = combined[:max_chars]
    return combined
