"""Post-process assistant responses for consistent Markdown structure."""

from __future__ import annotations

import re

_INTERNAL_LABEL_PATTERNS = [
    re.compile(r"^#+\s*(ROUTING PLAN|CONVERSATION SUMMARY|ORGANIZED ANSWER)\s*$", re.I | re.M),
    re.compile(r"^#+\s*(User Intent|Important Facts|Decisions Made|Technical Topics)\s*$", re.I | re.M),
]

_CITATION_INLINE = re.compile(r"\[S(\d+)\]")


def _strip_internal_sections(text: str) -> str:
    cleaned = text or ""
    for pattern in _INTERNAL_LABEL_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    return cleaned


def _normalize_headings(text: str) -> str:
    lines = (text or "").splitlines()
    normalized: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") and not stripped.startswith("# "):
            # Ensure space after hash marks for ATX headings.
            hashes = len(stripped) - len(stripped.lstrip("#"))
            title = stripped[hashes:].strip()
            normalized.append(f"{'#' * hashes} {title}" if title else stripped)
        else:
            normalized.append(line)
    return "\n".join(normalized).strip()


def _ensure_summary_heading(text: str) -> str:
    body = (text or "").strip()
    if not body:
        return body
    if re.search(r"^#\s+Summary\b", body, re.I | re.M):
        return body
    if re.search(r"^#\s+Executive Summary\b", body, re.I | re.M):
        return body
    if is_simple_response(body):
        return body
    return f"# Summary\n\n{body}"


def is_simple_response(text: str) -> bool:
    """Heuristic: short conversational replies should not get report headings."""
    body = (text or "").strip()
    if not body:
        return True
    if len(body) > 280:
        return False
    if re.search(r"^#+\s", body, re.M):
        return False
    sentence_count = len(re.findall(r"[.!?]+", body))
    return sentence_count <= 2 and len(body.split()) <= 40


def normalize_citations(text: str) -> str:
    """Keep [S#] labels intact; trim stray spaces before citations."""
    return _CITATION_INLINE.sub(lambda m: f" [S{m.group(1)}]", text).replace("  [S", " [S")


def format_assistant_response(text: str, *, query: str = "") -> str:
    """Normalize assistant Markdown before persistence or final display."""
    from app.services.conversation_heuristics import is_simple_conversational_query

    body = (text or "").strip()
    if not body:
        return body

    if is_simple_conversational_query(query) or is_simple_response(body):
        return body

    body = _strip_internal_sections(body)
    body = _normalize_headings(body)
    body = normalize_citations(body)
    body = _ensure_summary_heading(body)

    # Collapse excessive blank lines.
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()
