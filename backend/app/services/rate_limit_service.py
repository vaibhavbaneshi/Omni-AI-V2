"""Shared rate-limit path rules and client identification."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from urllib.parse import urlencode

from starlette.requests import Request

from app.core.app_settings import get_settings


EXEMPT_PATHS = {
    "/health",
    "/health/live",
    "/health/ready",
    "/health/migrations",
    "/",
    "/docs",
    "/openapi.json",
}

# OAuth redirects must not return raw JSON to the browser during sign-in.
OAUTH_FLOW_PREFIXES = (
    "/auth/github",
    "/auth/google",
)


@dataclass(frozen=True)
class RateLimitRule:
    limit: int
    window_seconds: int
    scope: str


def is_test_mode_enabled() -> bool:
    return os.environ.get("TEST_MODE", "").strip().lower() in {"1", "true", "yes"}


def is_rate_limit_exempt_path(path: str) -> bool:
    if is_test_mode_enabled():
        return True
    if path in EXEMPT_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in OAUTH_FLOW_PREFIXES)


def is_browser_navigation(request: Request) -> bool:
    if request.headers.get("sec-fetch-mode") == "navigate":
        return True
    accept = request.headers.get("accept", "")
    return "text/html" in accept.lower()


def browser_rate_limit_redirect_url(*, retry_after: int, scope: str) -> str:
    frontend = get_settings().FRONTEND_URL.strip().rstrip("/")
    params = urlencode({"retry_after": str(max(1, retry_after)), "scope": scope})
    return f"{frontend}/rate-limited?{params}"


def rule_for_path(path: str, *, default_limit: int = 120) -> RateLimitRule:
    if path.startswith("/upload"):
        return RateLimitRule(limit=10, window_seconds=3600, scope="uploads")
    if path.startswith("/chat"):
        return RateLimitRule(limit=30, window_seconds=60, scope="chat")
    if path.startswith("/auth/"):
        return RateLimitRule(limit=30, window_seconds=60, scope="auth")
    return RateLimitRule(limit=max(min(default_limit, 1000), 1), window_seconds=60, scope="api")


def client_ip_from_scope(scope: dict) -> str:
    forwarded_for = None
    for name, value in scope.get("headers", []):
        if name.lower() == b"x-forwarded-for":
            forwarded_for = value.decode("latin-1").split(",")[0].strip()
            break
    client = scope.get("client")
    return forwarded_for or (client[0] if client else "unknown")


def client_ip_from_request(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def bucket_key(*, client_ip: str, scope_name: str) -> str:
    return f"{client_ip}:{scope_name}"


def rate_limit_headers(*, limit: int, remaining: int, reset_seconds: int) -> dict[str, str]:
    return {
        "Retry-After": str(reset_seconds),
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(reset_seconds),
    }


def reset_seconds_for_window(*, window_start: float, window_seconds: int, now: float | None = None) -> int:
    current = now if now is not None else time.time()
    return int(max(1, window_start + window_seconds - current))
