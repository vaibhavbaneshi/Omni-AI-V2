"""Shared rate-limit path rules and client identification."""

from __future__ import annotations

import time
from dataclasses import dataclass

from starlette.requests import Request


EXEMPT_PATHS = {
    "/health",
    "/health/live",
    "/health/ready",
    "/health/migrations",
    "/",
    "/docs",
    "/openapi.json",
}


@dataclass(frozen=True)
class RateLimitRule:
    limit: int
    window_seconds: int
    scope: str


def rule_for_path(path: str, *, default_limit: int = 120) -> RateLimitRule:
    if path.startswith("/upload"):
        return RateLimitRule(limit=10, window_seconds=3600, scope="uploads")
    if path.startswith("/chat"):
        return RateLimitRule(limit=30, window_seconds=60, scope="chat")
    if path.startswith("/auth/"):
        return RateLimitRule(limit=10, window_seconds=60, scope="auth")
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
