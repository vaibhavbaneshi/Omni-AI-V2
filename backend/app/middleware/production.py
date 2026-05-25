"""Production middleware: trace IDs, security headers, rate limiting."""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.app_settings import get_settings
from app.core.telemetry import new_trace_id, set_trace_context

logger = logging.getLogger("omni.http")


class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("x-trace-id") or new_trace_id()
        set_trace_context(trace_id=trace_id)
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Response-Time-Ms"] = str(duration_ms)
        logger.info(
            "request.complete method=%s path=%s status=%s duration_ms=%s trace_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            trace_id,
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        settings = get_settings()
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    """Simple per-IP sliding window limiter (use Redis in multi-worker production)."""

    def __init__(self, app, requests_per_minute: int = 120):
        super().__init__(app)
        self.limit = max(requests_per_minute, 1)
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in {"/health", "/", "/docs", "/openapi.json"}:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - 60
        bucket = self._hits[client_ip]

        while bucket and bucket[0] < window_start:
            bucket.popleft()

        if len(bucket) >= self.limit:
            return Response(
                content='{"detail":"Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
            )

        bucket.append(now)
        return await call_next(request)
