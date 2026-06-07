"""Production middleware: trace IDs, security headers, rate limiting.

Uses pure ASGI middleware so StreamingResponse bodies are not buffered.
BaseHTTPMiddleware breaks SSE/NDJSON streaming on Railway and other proxies.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from typing import Callable

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.app_settings import get_settings
from app.core.telemetry import new_trace_id, set_trace_context
from app.services.usage_tracking_service import record_api_usage

logger = logging.getLogger("omni.http")

SendCallable = Callable[[Message], None]


class TraceMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        trace_id = ""
        for name, value in scope.get("headers", []):
            if name.lower() == b"x-trace-id":
                trace_id = value.decode("latin-1")
                break
        if not trace_id:
            trace_id = new_trace_id()

        set_trace_context(trace_id=trace_id)
        started = time.perf_counter()
        request = Request(scope, receive=receive)
        status_code = 500
        auth_header = None
        for name, value in scope.get("headers", []):
            if name.lower() == b"authorization":
                auth_header = value.decode("latin-1")
                break

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-trace-id", trace_id.encode("latin-1")))
                message = {**message, "headers": headers}
            elif message["type"] == "http.response.body" and not message.get("more_body", False):
                duration_ms = round((time.perf_counter() - started) * 1000, 2)
                headers = list(message.get("headers", []))
                headers.append((b"x-response-time-ms", str(duration_ms).encode("latin-1")))
                message = {**message, "headers": headers}
                logger.info(
                    "request.complete method=%s path=%s status=%s duration_ms=%s trace_id=%s",
                    request.method,
                    request.url.path,
                    status_code,
                    duration_ms,
                    trace_id,
                )
                record_api_usage(
                    method=request.method,
                    path=request.url.path,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    authorization=auth_header,
                    trace_id=trace_id,
                )
            await send(message)

        await self.app(scope, receive, send_wrapper)


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        settings = get_settings()

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"strict-origin-when-cross-origin"),
                        (
                            b"permissions-policy",
                            b"camera=(), microphone=(), geolocation=(), payment=()",
                        ),
                        (
                            b"content-security-policy",
                            b"default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
                        ),
                    ]
                )
                if settings.ENVIRONMENT == "production":
                    headers.append(
                        (
                            b"strict-transport-security",
                            b"max-age=31536000; includeSubDomains",
                        )
                    )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)


class InMemoryRateLimitMiddleware:
    """Simple per-IP sliding window limiter (use Redis in multi-worker production)."""

    def __init__(self, app: ASGIApp, requests_per_minute: int = 120):
        self.app = app
        self.default_limit = max(min(requests_per_minute, 100), 1)
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _rule_for_path(self, path: str) -> tuple[int, int, str]:
        if path.startswith("/upload"):
            return 10, 3600, "uploads"
        if path.startswith("/chat"):
            return 30, 60, "chat"
        if path.startswith("/auth/"):
            return 10, 60, "auth"
        return self.default_limit, 60, "api"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in {"/health", "/health/live", "/", "/docs", "/openapi.json"}:
            await self.app(scope, receive, send)
            return

        forwarded_for = None
        for name, value in scope.get("headers", []):
            if name.lower() == b"x-forwarded-for":
                forwarded_for = value.decode("latin-1").split(",")[0].strip()
                break
        client = scope.get("client")
        client_ip = forwarded_for or (client[0] if client else "unknown")
        now = time.time()
        limit, window_seconds, scope_name = self._rule_for_path(path)
        window_start = now - window_seconds
        bucket_key = f"{client_ip}:{scope_name}"
        bucket = self._hits[bucket_key]

        while bucket and bucket[0] < window_start:
            bucket.popleft()

        reset_seconds = int(max(1, (bucket[0] + window_seconds - now) if bucket else window_seconds))

        if len(bucket) >= limit:
            response = JSONResponse(
                content={"detail": "Rate limit exceeded"},
                status_code=429,
                headers={
                    "Retry-After": str(reset_seconds),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_seconds),
                },
            )
            await response(scope, receive, send)
            return

        bucket.append(now)

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                remaining = max(0, limit - len(bucket))
                headers.extend(
                    [
                        (b"x-ratelimit-limit", str(limit).encode("latin-1")),
                        (b"x-ratelimit-remaining", str(remaining).encode("latin-1")),
                        (b"x-ratelimit-reset", str(reset_seconds).encode("latin-1")),
                    ]
                )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)
