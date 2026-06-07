"""Rewrite follow-up chat queries into standalone retrieval queries."""

from __future__ import annotations

import logging
import re

from app.core.app_settings import get_settings
from app.services.llm_invoke import invoke_generate

logger = logging.getLogger(__name__)

_FOLLOWUP_PATTERNS = [
    re.compile(r"\b(expand|elaborate|explain more|tell me more|go on|continue|clarify)\b", re.I),
    re.compile(r"\b(point|item|step|section|paragraph|bullet)\s*#?\s*\d+\b", re.I),
    re.compile(r"\b(that|this|it|those|these|them|above|previous|earlier|same)\b", re.I),
    re.compile(r"^(yes|no|ok|okay|sure|why|how so|what do you mean)\b", re.I),
    re.compile(r"\bwhat about\b", re.I),
    re.compile(r"^(and|also|but|then)\b", re.I),
    re.compile(r"\b(in|on|about)\s+(that|this|it)\b", re.I),
]

_STANDALONE_HINTS = re.compile(
    r"\b(compare|summarize|explain|what is|how do|define|analyze|analyse|review)\b",
    re.I,
)


def needs_contextualization(query: str, history: str = "") -> bool:
    """Return True when the query likely depends on prior conversation turns."""
    text = (query or "").strip()
    history = (history or "").strip()

    if not text or not history:
        return False

    if any(pattern.search(text) for pattern in _FOLLOWUP_PATTERNS):
        return True

    if _STANDALONE_HINTS.search(text):
        return False

    if len(text) >= 180:
        return False

    word_count = len(text.split())
    return word_count <= 14


def _heuristic_contextualize(query: str, history: str) -> str:
    """Cheap fallback when LLM rewriting is disabled or fails."""
    lines = [line.strip() for line in history.splitlines() if line.strip()]
    last_user = next((line for line in reversed(lines) if line.lower().startswith("user:")), "")
    last_assistant = next(
        (line for line in reversed(lines) if line.lower().startswith("assistant:")),
        "",
    )

    subject = last_user.removeprefix("user:").strip() or last_assistant.removeprefix("assistant:").strip()
    if not subject:
        return query

    if len(subject) > 240:
        subject = subject[:240].rsplit(" ", 1)[0] + "..."

    return f"{query.strip()} — in context of: {subject}"


def contextualize_query(
    query: str,
    *,
    history: str = "",
    summary: str = "",
    user_id: int | None = None,
    session_id: int | None = None,
) -> str:
    """Expand a follow-up into a standalone retrieval query."""
    text = (query or "").strip()
    if not needs_contextualization(text, history):
        return text

    settings = get_settings()
    if not settings.ENABLE_QUERY_REWRITING:
        return _heuristic_contextualize(text, history)

    history_block = (history or "").strip()
    if len(history_block) > 3000:
        history_block = history_block[-3000:]

    summary_block = (summary or "").strip()
    summary_section = f"\nConversation summary:\n{summary_block}\n" if summary_block else ""

    prompt = f"""Rewrite the follow-up question into one standalone search query.
Use the conversation history to resolve pronouns and references like "point 3" or "that".
Output ONLY the rewritten query — no quotes, labels, or explanation.

{summary_section}Recent conversation:
{history_block}

Follow-up question: {text}

Standalone search query:"""

    try:
        rewritten = invoke_generate(
            prompt,
            temperature=0.1,
            timeout=30,
            endpoint="rag.query_rewrite",
            user_id=user_id,
            session_id=session_id,
        )
        cleaned = (rewritten or "").strip().strip('"').strip("'")
        if cleaned and len(cleaned) >= 3:
            logger.info(
                "Query contextualized session_id=%s original=%r rewritten=%r",
                session_id,
                text[:80],
                cleaned[:120],
            )
            return cleaned
    except Exception:
        logger.exception("Query contextualization failed; using heuristic fallback")

    return _heuristic_contextualize(text, history)


def resolve_retrieval_query(
    query: str,
    *,
    history: str = "",
    summary: str = "",
    user_id: int | None = None,
    session_id: int | None = None,
) -> tuple[str, str | None]:
    """Return (retrieval_query, original_query_if_rewritten)."""
    text = (query or "").strip()
    retrieval_query = contextualize_query(
        text,
        history=history,
        summary=summary,
        user_id=user_id,
        session_id=session_id,
    )
    if retrieval_query != text:
        return retrieval_query, text
    return text, None
