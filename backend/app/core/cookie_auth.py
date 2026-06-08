"""HttpOnly cookie helpers for OAuth session tokens."""

from __future__ import annotations

import secrets
from typing import Any

from fastapi import Request, Response

from app.core.app_settings import get_settings

ACCESS_COOKIE = "omniai_access"
REFRESH_COOKIE = "omniai_refresh"
CSRF_COOKIE = "omniai_csrf"
CSRF_HEADER = "X-CSRF-Token"


def _cookie_secure() -> bool:
    return get_settings().ENVIRONMENT == "production"


def _cookie_samesite() -> str:
    return "none" if _cookie_secure() else "lax"


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
