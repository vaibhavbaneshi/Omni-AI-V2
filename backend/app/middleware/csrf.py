"""CSRF protection for cookie-authenticated mutating requests."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.cookie_auth import ACCESS_COOKIE, validate_csrf
from app.core.cors_utils import cors_headers_for_request

SAFE_PREFIXES = (
    "/auth/github",
    "/auth/google",
    "/auth/refresh",
    "/auth/logout",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
)


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(prefix) for prefix in SAFE_PREFIXES):
            return await call_next(request)

        auth_header = (request.headers.get("authorization") or "").strip()
        if auth_header.lower().startswith("bearer "):
            return await call_next(request)

        if ACCESS_COOKIE not in request.cookies:
            return await call_next(request)

        if not validate_csrf(request):
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF validation failed."},
                headers=cors_headers_for_request(request),
            )

        return await call_next(request)
