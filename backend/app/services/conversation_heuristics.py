"""Lightweight heuristics for conversational vs research-heavy chat turns."""

from __future__ import annotations

import re

_GREETING = re.compile(
    r"^(hi|hello|hey|hiya|yo|sup|thanks|thank you|thx|ok|okay|yes|no|now|"
    r"good morning|good afternoon|good evening|how are you|what's up|whats up)"
    r"[\s!.?,]*$",
    re.I,
)

_RESEARCH_MARKERS = re.compile(
    r"\b(what|why|how|when|where|who|explain|analyze|compare|summarize|research|"
    r"document|file|pdf|code|implement|write|help me)\b",
    re.I,
)


def is_simple_conversational_query(query: str) -> bool:
    """True for short greetings/acknowledgements that should not trigger web search or long templates."""
    text = (query or "").strip()
    if not text:
        return False

    if _RESEARCH_MARKERS.search(text):
        return False

    if len(text) <= 20 and _GREETING.match(text):
        return True

    words = text.split()
    if len(words) <= 2 and "?" not in text and len(text) <= 24:
        return True

    return False
