"""HttpOnly cookie helpers for OAuth session tokens."""

from __future__ import annotations

import secrets
from typing import Any
from urllib.parse import urlparse

from fastapi import Request, Response

from app.core.app_settings import get_settings

ACCESS_COOKIE = "omniai_access"
REFRESH_COOKIE = "omniai_refresh"
CSRF_COOKIE = "omniai_csrf"
CSRF_HEADER = "X-CSRF-Token"


def _is_cross_origin_auth() -> bool:
    """True when the SPA and API are on different origins (e.g. Vercel + Railway)."""
    settings = get_settings()
    try:
        frontend = urlparse(settings.FRONTEND_URL.strip().rstrip("/"))
        api = urlparse(settings.API_PUBLIC_URL.strip().rstrip("/"))
        return (frontend.scheme, frontend.netloc) != (api.scheme, api.netloc)
    except Exception:
        return settings.ENVIRONMENT in {"production", "staging"}


def _cookie_secure() -> bool:
    settings = get_settings()
    if settings.ENVIRONMENT in {"production", "staging"}:
        return True
    return settings.API_PUBLIC_URL.strip().lower().startswith("https://")


def _cookie_samesite() -> str:
    if _cookie_secure() or _is_cross_origin_auth():
        return "none"
    return "lax"


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_auth_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str,
    csrf_token: str | None = None,
) -> str:
    csrf = csrf_token or generate_csrf_token()
    common: dict[str, Any] = {
        "httponly": True,
        "secure": _cookie_secure(),
        "samesite": _cookie_samesite(),
        "path": "/",
    }
    response.set_cookie(ACCESS_COOKIE, access_token, max_age=60 * 15, **common)
    response.set_cookie(REFRESH_COOKIE, refresh_token, max_age=60 * 60 * 24 * 14, **common)
    response.set_cookie(
        CSRF_COOKIE,
        csrf,
        httponly=False,
        secure=_cookie_secure(),
        samesite=_cookie_samesite(),
        path="/",
        max_age=60 * 60 * 24 * 14,
    )
    return csrf


def clear_auth_cookies(response: Response) -> None:
    for name in (ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE):
        response.delete_cookie(name, path="/")


def get_access_token_from_request(request: Request) -> str | None:
    cookie = request.cookies.get(ACCESS_COOKIE)
    if cookie:
        return cookie
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return None


def get_refresh_token_from_request(request: Request) -> str | None:
    return request.cookies.get(REFRESH_COOKIE)


def validate_csrf(request: Request) -> bool:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return True
    cookie_csrf = request.cookies.get(CSRF_COOKIE)
    header_csrf = request.headers.get(CSRF_HEADER)
    if not cookie_csrf or not header_csrf:
        return False
    return secrets.compare_digest(cookie_csrf, header_csrf)
