"""AI telemetry: trace context, structured events, optional LangSmith."""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, TypeVar

from app.core.app_settings import get_settings

logger = logging.getLogger("omni.telemetry")

_trace_id: ContextVar[str] = ContextVar("trace_id", default="")
_user_id: ContextVar[str] = ContextVar("user_id", default="")

F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class LLMCallMetrics:
    """Captured once per LLM invocation for DB analytics and LangSmith metadata."""

    provider: str
    model: str
    endpoint: str
    prompt_chars: int = 0
    completion_chars: int = 0
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: float = 0.0
    success: bool = True
    error_message: str | None = None
    trace_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def get_trace_id() -> str:
    trace = _trace_id.get()
    return trace or "no-trace"


def set_trace_context(*, trace_id: str, user_id: str | int | None = None) -> None:
    _trace_id.set(trace_id)
    _user_id.set(str(user_id) if user_id is not None else "")


def estimate_tokens(text: str) -> int:
    """Rough token estimate when provider usage metadata is unavailable."""
    if not text:
        return 0
    return max(1, len(text) // 4)


@dataclass
class SpanEvent:
    name: str
    duration_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)


@contextmanager
def traced_span(name: str, **metadata: Any) -> Iterator[SpanEvent]:
    started = time.perf_counter()
    event = SpanEvent(name=name, duration_ms=0.0, metadata=metadata)
    _log_event("span.start", name=name, **metadata)
    try:
        yield event
    finally:
        event.duration_ms = round((time.perf_counter() - started) * 1000, 2)
        _log_event("span.end", name=name, duration_ms=event.duration_ms, **metadata)


def new_trace_id() -> str:
    return str(uuid.uuid4())


def _log_event(event: str, **fields: Any) -> None:
    payload = {
        "event": event,
        "trace_id": get_trace_id(),
        "user_id": _user_id.get(),
        **fields,
    }
    logger.info(json.dumps(payload, default=str))


def log_llm_metrics(metrics: LLMCallMetrics) -> None:
    """Structured log line for every LLM call — complements LangSmith and DB tables."""
    _log_event(
        "llm.complete",
        provider=metrics.provider,
        model=metrics.model,
        endpoint=metrics.endpoint,
        latency_ms=metrics.latency_ms,
        prompt_chars=metrics.prompt_chars,
        completion_chars=metrics.completion_chars,
        prompt_tokens=metrics.prompt_tokens,
        completion_tokens=metrics.completion_tokens,
        total_tokens=metrics.total_tokens,
        success=metrics.success,
        error=metrics.error_message,
    )


def langsmith_trace(name: str, *, run_type: str = "chain") -> Callable[[F], F]:
    """Decorator that no-ops when LangSmith is disabled — safe for Railway defaults."""
    settings = get_settings()
    if not settings.LANGCHAIN_TRACING_V2 or not settings.LANGCHAIN_API_KEY:
        return lambda fn: fn

    try:
        from langsmith import traceable

        return traceable(name=name, run_type=run_type)  # type: ignore[return-value]
    except Exception:
        logger.debug("LangSmith traceable unavailable for %s", name)
        return lambda fn: fn
