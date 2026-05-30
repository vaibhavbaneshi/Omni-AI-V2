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
        self.limit = max(requests_per_minute, 1)
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in {"/health", "/", "/docs", "/openapi.json"}:
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        now = time.time()
        window_start = now - 60
        bucket = self._hits[client_ip]

        while bucket and bucket[0] < window_start:
            bucket.popleft()

        if len(bucket) >= self.limit:
            response = JSONResponse(
                content={"detail": "Rate limit exceeded"},
                status_code=429,
            )
            await response(scope, receive, send)
            return

        bucket.append(now)
        await self.app(scope, receive, send)
