"""Map internal exceptions to safe, user-facing messages."""

from __future__ import annotations

import logging

from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

DEFAULT_USER_MESSAGE = "Something went wrong. Please try again."
CHAT_USER_MESSAGE = "We couldn't generate a response. Please try again."

_INTERNAL_MARKERS = (
    "sqlalchemy",
    "psycopg2",
    "postgresql",
    "traceback",
    "[sql:",
    "line 2:",
    "undefinedtable",
    "relation ",
    "integrityerror",
    "operationalerror",
    "parameters:",
    "background on this error",
    "stream_options",
    "completions.create",
    "unexpected keyword argument",
    "groq streaming failed",
    "openai streaming failed",
    "deepseek streaming failed",
    "llmprovidererror",
)


def _looks_internal(message: str) -> bool:
    lower = message.lower()
    return any(marker in lower for marker in _INTERNAL_MARKERS)


def user_facing_message(exc: Exception, *, context: str = "request") -> str:
    """Log the full exception server-side; return a safe message for clients."""
    logger.exception("%s failed", context, exc_info=exc)

    if isinstance(exc, ValueError):
        message = str(exc).strip()
        if message and len(message) <= 200 and not _looks_internal(message):
            return message

    if isinstance(exc, SQLAlchemyError):
        lowered = str(exc).lower()
        if "does not exist" in lowered or "undefinedtable" in lowered:
            return "Sign-in is temporarily unavailable while the database is being set up. Please try again shortly."
        return "We couldn't complete your request right now. Please try again."

    message = str(exc).strip()
    if not message or _looks_internal(message) or len(message) > 200:
        return DEFAULT_USER_MESSAGE

    return message


def chat_facing_message(exc: Exception, *, context: str = "chat") -> str:
    """Safe message for chat stream error events."""
    from app.core.llm import LLMProviderError

    logger.exception("%s failed", context, exc_info=exc)

    if isinstance(exc, LLMProviderError):
        lowered = str(exc).lower()
        if "not configured" in lowered or "api_key" in lowered:
            return "AI service is temporarily unavailable. Please try again later."
        if "rate" in lowered or "429" in lowered:
            return "The AI service is busy. Please wait a moment and try again."
        return CHAT_USER_MESSAGE

    return user_facing_message(exc, context=context)
