"""AI telemetry: trace context, structured events, optional LangSmith."""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Iterator

from app.core.app_settings import get_settings

logger = logging.getLogger("omni.telemetry")

_trace_id: ContextVar[str] = ContextVar("trace_id", default="")
_user_id: ContextVar[str] = ContextVar("user_id", default="")


def get_trace_id() -> str:
    trace = _trace_id.get()
    return trace or "no-trace"


def set_trace_context(*, trace_id: str, user_id: str | int | None = None) -> None:
    _trace_id.set(trace_id)
    _user_id.set(str(user_id) if user_id is not None else "")


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


def maybe_trace_llm_call(*, name: str, inputs: dict[str, Any]) -> None:
    settings = get_settings()
    if not settings.LANGCHAIN_TRACING_V2:
        return
    try:
        from langsmith import traceable  # type: ignore

        @traceable(name=name, run_type="llm")
        def _noop(payload: dict[str, Any]) -> dict[str, Any]:
            return payload

        _noop(inputs)
    except Exception:
        logger.debug("LangSmith tracing unavailable for %s", name)
