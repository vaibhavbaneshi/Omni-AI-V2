"""Helpers to attach CORS headers on responses that bypass the normal middleware path."""

from __future__ import annotations

from starlette.requests import Request

from app.core.app_settings import get_settings


def cors_headers_for_request(request: Request) -> dict[str, str]:
    """Return Access-Control-* headers when the request Origin is allow-listed."""
    origin = (request.headers.get("origin") or "").strip()
    if not origin:
        return {}

    allowed = set(get_settings().cors_origin_list)
    if origin not in allowed:
        return {}

    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Vary": "Origin",
    }
