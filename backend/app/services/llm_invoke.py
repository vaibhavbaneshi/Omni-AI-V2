"""Central LLM invocation layer with latency, token, and LangSmith tracing.

All production LLM calls should go through this module so observability stays consistent.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

from app.core.llm import BaseLLMProvider, get_llm
from app.core.telemetry import (
    LLMCallMetrics,
    estimate_tokens,
    langsmith_trace,
    log_llm_metrics,
    traced_span,
    get_trace_id,
)
from app.services.usage_tracking_service import record_llm_usage


def _finalize_tokens(metrics: LLMCallMetrics) -> None:
    if metrics.prompt_tokens is None and metrics.prompt_chars:
        metrics.prompt_tokens = estimate_tokens("x" * metrics.prompt_chars)
    if metrics.completion_tokens is None and metrics.completion_chars:
        metrics.completion_tokens = estimate_tokens("x" * metrics.completion_chars)
    if metrics.total_tokens is None and (
        metrics.prompt_tokens is not None or metrics.completion_tokens is not None
    ):
        metrics.total_tokens = (metrics.prompt_tokens or 0) + (metrics.completion_tokens or 0)


def _persist_metrics(
    metrics: LLMCallMetrics,
    *,
    user_id: int | None = None,
    session_id: int | None = None,
) -> None:
    metrics.trace_id = metrics.trace_id or get_trace_id()
    _finalize_tokens(metrics)
    log_llm_metrics(metrics)
    record_llm_usage(metrics, user_id=user_id, session_id=session_id)


@langsmith_trace("omni.llm.generate", run_type="llm")
def invoke_generate(
    prompt: str,
    *,
    temperature: float = 0.35,
    timeout: int = 120,
    endpoint: str = "llm.generate",
    user_id: int | None = None,
    session_id: int | None = None,
    provider: BaseLLMProvider | None = None,
) -> str:
    llm = provider or get_llm()
    metrics = LLMCallMetrics(
        provider=llm.name,
        model=llm.model_name,
        endpoint=endpoint,
        prompt_chars=len(prompt),
    )
    started = time.perf_counter()

    with traced_span(endpoint, provider=llm.name, model=llm.model_name):
        try:
            result = llm.generate(prompt, temperature=temperature, timeout=timeout)
            usage = getattr(llm, "last_usage", None)
            if isinstance(usage, dict):
                metrics.prompt_tokens = usage.get("prompt_tokens")
                metrics.completion_tokens = usage.get("completion_tokens")
                metrics.total_tokens = usage.get("total_tokens")
            metrics.completion_chars = len(result)
            metrics.latency_ms = round((time.perf_counter() - started) * 1000, 2)
            metrics.success = True
            _persist_metrics(metrics, user_id=user_id, session_id=session_id)
            return result
        except Exception as exc:
            metrics.latency_ms = round((time.perf_counter() - started) * 1000, 2)
            metrics.success = False
            metrics.error_message = str(exc)
            _persist_metrics(metrics, user_id=user_id, session_id=session_id)
            raise


def invoke_stream(
    prompt: str,
    *,
    temperature: float = 0.35,
    timeout: int = 120,
    endpoint: str = "llm.stream",
    user_id: int | None = None,
    session_id: int | None = None,
    provider: BaseLLMProvider | None = None,
) -> Iterator[str]:
    llm = provider or get_llm()
    metrics = LLMCallMetrics(
        provider=llm.name,
        model=llm.model_name,
        endpoint=endpoint,
        prompt_chars=len(prompt),
    )
    started = time.perf_counter()
    completion_parts: list[str] = []

    with traced_span(endpoint, provider=llm.name, model=llm.model_name):
        try:
            for token in llm.stream_generate(prompt, temperature=temperature, timeout=timeout):
                completion_parts.append(token)
                yield token

            usage = getattr(llm, "last_usage", None)
            if isinstance(usage, dict):
                metrics.prompt_tokens = usage.get("prompt_tokens")
                metrics.completion_tokens = usage.get("completion_tokens")
                metrics.total_tokens = usage.get("total_tokens")

            metrics.completion_chars = sum(len(part) for part in completion_parts)
            metrics.latency_ms = round((time.perf_counter() - started) * 1000, 2)
            metrics.success = True
            _persist_metrics(metrics, user_id=user_id, session_id=session_id)
        except Exception as exc:
            metrics.completion_chars = sum(len(part) for part in completion_parts)
            metrics.latency_ms = round((time.perf_counter() - started) * 1000, 2)
            metrics.success = False
            metrics.error_message = str(exc)
            _persist_metrics(metrics, user_id=user_id, session_id=session_id)
            raise
