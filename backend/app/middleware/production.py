"""Production middleware: trace IDs, security headers, rate limiting.

Uses pure ASGI middleware so StreamingResponse bodies are not buffered.
BaseHTTPMiddleware breaks SSE/NDJSON streaming on Railway and other proxies.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict, deque
from typing import Callable

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.app_settings import get_settings
from app.core.telemetry import new_trace_id, set_trace_context
from app.services.abuse_detection_service import record_rate_limit_event
from app.services.rate_limit_service import (
    EXEMPT_PATHS,
    bucket_key,
    client_ip_from_scope,
    rate_limit_headers,
    reset_seconds_for_window,
    rule_for_path,
)
from app.services.usage_tracking_service import record_api_usage

logger = logging.getLogger("omni.http")

SendCallable = Callable[[Message], Send]


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


def _encode_rate_limit_headers(headers: dict[str, str]) -> list[tuple[bytes, bytes]]:
    return [(key.lower().encode("latin-1"), value.encode("latin-1")) for key, value in headers.items()]


class InMemoryRateLimitMiddleware:
    """Simple per-IP sliding window limiter for single-process development."""

    def __init__(self, app: ASGIApp, requests_per_minute: int = 120):
        self.app = app
        self.default_limit = max(min(requests_per_minute, 1000), 1)
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return

        client_ip = client_ip_from_scope(scope)
        now = time.time()
        rule = rule_for_path(path, default_limit=self.default_limit)
        window_start = now - rule.window_seconds
        key = bucket_key(client_ip=client_ip, scope_name=rule.scope)
        bucket = self._hits[key]

        while bucket and bucket[0] < window_start:
            bucket.popleft()

        reset_seconds = reset_seconds_for_window(
            window_start=bucket[0] if bucket else now,
            window_seconds=rule.window_seconds,
            now=now,
        )

        if len(bucket) >= rule.limit:
            record_rate_limit_event(
                db=None,
                client_ip=client_ip,
                path=path,
                scope_name=rule.scope,
                limit=rule.limit,
            )
            response = JSONResponse(
                content={"detail": "Rate limit exceeded"},
                status_code=429,
                headers=rate_limit_headers(
                    limit=rule.limit,
                    remaining=0,
                    reset_seconds=reset_seconds,
                ),
            )
            await response(scope, receive, send)
            return

        bucket.append(now)
        remaining = max(0, rule.limit - len(bucket))

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    _encode_rate_limit_headers(
                        rate_limit_headers(
                            limit=rule.limit,
                            remaining=remaining,
                            reset_seconds=reset_seconds,
                        )
                    )
                )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)


class RedisRateLimitMiddleware:
    """Distributed sliding-window limiter backed by Redis sorted sets."""

    def __init__(self, app: ASGIApp, requests_per_minute: int = 120):
        self.app = app
        self.default_limit = max(min(requests_per_minute, 1000), 1)
        self._fallback = InMemoryRateLimitMiddleware(app, requests_per_minute=requests_per_minute)

    def _check_redis(self, *, key: str, rule) -> tuple[bool, int, int] | None:
        from app.core.redis_client import try_get_redis_connection

        redis = try_get_redis_connection()
        if redis is None:
            return None

        now = time.time()
        redis_key = f"ratelimit:{key}"
        member = f"{now}:{uuid.uuid4().hex}"

        try:
            pipe = redis.pipeline()
            pipe.zremrangebyscore(redis_key, 0, now - rule.window_seconds)
            pipe.zadd(redis_key, {member: now})
            pipe.zcard(redis_key)
            pipe.expire(redis_key, rule.window_seconds + 5)
            _, _, count, _ = pipe.execute()
            remaining = max(0, rule.limit - int(count))
            reset_seconds = int(rule.window_seconds)
            allowed = int(count) <= rule.limit
            return allowed, remaining, reset_seconds
        except Exception:
            logger.exception("Redis rate limit check failed; falling back to in-memory limiter")
            return None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return

        client_ip = client_ip_from_scope(scope)
        rule = rule_for_path(path, default_limit=self.default_limit)
        key = bucket_key(client_ip=client_ip, scope_name=rule.scope)
        result = self._check_redis(key=key, rule=rule)

        if result is None:
            await self._fallback(scope, receive, send)
            return

        allowed, remaining, reset_seconds = result
        if not allowed:
            record_rate_limit_event(
                db=None,
                client_ip=client_ip,
                path=path,
                scope_name=rule.scope,
                limit=rule.limit,
            )
            response = JSONResponse(
                content={"detail": "Rate limit exceeded"},
                status_code=429,
                headers=rate_limit_headers(
                    limit=rule.limit,
                    remaining=0,
                    reset_seconds=reset_seconds,
                ),
            )
            await response(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    _encode_rate_limit_headers(
                        rate_limit_headers(
                            limit=rule.limit,
                            remaining=remaining,
                            reset_seconds=reset_seconds,
                        )
                    )
                )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)


def create_rate_limit_middleware(app: ASGIApp) -> ASGIApp:
    settings = get_settings()
    if settings.use_redis_rate_limit:
        logger.info("Rate limiting: Redis-backed (multi-worker safe)")
        return RedisRateLimitMiddleware(app, requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)
    logger.info("Rate limiting: in-memory (single-process)")
    return InMemoryRateLimitMiddleware(app, requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)
