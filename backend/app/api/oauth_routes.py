from urllib.parse import urlencode

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.oauth_config import get_oauth_settings, oauth_providers_status
from app.core.safe_errors import user_facing_message
from app.db.session import get_db
from app.models.user_settings import UserSessionRecord
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_refresh_token,
    refresh_token_expires_at,
    verify_refresh_token,
)
from app.services.settings_service import register_user_session
from app.services.security_audit_service import audit_log
from app.services.oauth_service import (
    build_github_authorize_url,
    build_google_authorize_url,
    decode_oauth_state,
    encode_oauth_state,
    exchange_github_code,
    exchange_google_code,
    fetch_github_profile,
    fetch_google_profile,
    get_or_create_oauth_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=32, max_length=512)


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(default=None, max_length=512)


def _sanitize_next_path(next_path: str | None) -> str:
    if not next_path or not next_path.startswith("/"):
        return "/dashboard"
    if next_path.startswith("//"):
        return "/dashboard"
    return next_path


def _redirect_to_frontend_error(message: str, next_path: str = "/login") -> RedirectResponse:
    settings = get_oauth_settings()
    params = urlencode({"error": message, "next": next_path})
    return RedirectResponse(
        f"{settings['frontend_url']}/auth/callback?{params}",
        status_code=302,
    )


def _redirect_to_frontend_success(
    *,
    token: str,
    refresh_token: str,
    email: str,
    name: str,
    username: str,
    next_path: str,
) -> RedirectResponse:
    settings = get_oauth_settings()
    params = urlencode(
        {
            "token": token,
            "refresh_token": refresh_token,
            "email": email,
            "name": name,
            "username": username,
            "next": next_path,
        }
    )
    return RedirectResponse(
        f"{settings['frontend_url']}/auth/callback?{params}",
        status_code=302,
    )


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _issue_session_tokens(
    *,
    db: Session,
    user,
    request: Request,
) -> tuple[str, str]:
    access_token = create_access_token(data={"sub": user.username})
    payload = decode_access_token(access_token)
    refresh_token = create_refresh_token()
    register_user_session(
        db,
        user=user,
        session_jti=payload["jti"],
        refresh_token_hash=hash_refresh_token(refresh_token),
        refresh_expires_at=refresh_token_expires_at(),
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
    )
    audit_log(
        db,
        action="auth.session.created",
        user_id=user.id,
        ip_address=_client_ip(request),
        detail={"provider": user.oauth_provider or "local"},
    )
    return access_token, refresh_token


@router.get("/providers")
def oauth_providers():
    return oauth_providers_status()


@router.post("/refresh")
def refresh_session(
    payload: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    token_hash = hash_refresh_token(payload.refresh_token)
    record = (
        db.query(UserSessionRecord)
        .filter(
            UserSessionRecord.refresh_token_hash == token_hash,
            UserSessionRecord.revoked_at.is_(None),
        )
        .first()
    )

    if not record or not record.refresh_expires_at or record.refresh_expires_at <= datetime.utcnow():
        audit_log(
            db,
            action="auth.refresh.rejected",
            user_id=record.user_id if record else None,
            ip_address=_client_ip(request),
            detail={"reason": "expired_or_unknown"},
        )
        raise HTTPException(status_code=401, detail="Refresh token is invalid or expired.")

    access_token = create_access_token(data={"sub": record.user.username})
    decoded = decode_access_token(access_token)
    next_refresh_token = create_refresh_token()
    record.session_jti = decoded["jti"]
    record.refresh_token_hash = hash_refresh_token(next_refresh_token)
    record.refresh_expires_at = refresh_token_expires_at()
    record.last_active_at = datetime.utcnow()
    record.ip_address = _client_ip(request)
    record.user_agent = (request.headers.get("user-agent") or "")[:500] or None
    db.commit()

    audit_log(
        db,
        action="auth.refresh.rotated",
        user_id=record.user_id,
        ip_address=_client_ip(request),
        detail={"session_id": record.id},
    )
    return {
        "access_token": access_token,
        "refresh_token": next_refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout")
def logout_session(
    payload: LogoutRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    record = None
    if payload.refresh_token:
        record = (
            db.query(UserSessionRecord)
            .filter(UserSessionRecord.refresh_token_hash == hash_refresh_token(payload.refresh_token))
            .first()
        )
    if record and record.revoked_at is None:
        record.revoked_at = datetime.utcnow()
        db.commit()
        audit_log(
            db,
            action="auth.logout",
            user_id=record.user_id,
            ip_address=_client_ip(request),
            detail={"session_id": record.id},
        )
    return {"message": "Logged out"}


@router.get("/github")
def github_login(
    next: str = Query("/dashboard", alias="next"),
):
    settings = get_oauth_settings()

    if not settings["github_client_id"] or not settings["github_client_secret"]:
        raise HTTPException(
            status_code=503,
            detail="GitHub sign-in is not configured on the server.",
        )

    next_path = _sanitize_next_path(next)
    state = encode_oauth_state("github", next_path)
    redirect_uri = f"{settings['api_public_url']}/auth/github/callback"

    authorize_url = build_github_authorize_url(
        client_id=settings["github_client_id"],
        redirect_uri=redirect_uri,
        state=state,
    )
    return RedirectResponse(authorize_url, status_code=302)


@router.get("/github/callback")
def github_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    settings = get_oauth_settings()
    next_path = "/dashboard"

    if error:
        return _redirect_to_frontend_error(f"GitHub sign-in was cancelled: {error}")

    if not code or not state:
        return _redirect_to_frontend_error("Missing GitHub authorization response.")

    try:
        state_payload = decode_oauth_state(state)
        next_path = _sanitize_next_path(state_payload.get("next"))
        redirect_uri = f"{settings['api_public_url']}/auth/github/callback"

        access_token = exchange_github_code(
            client_id=settings["github_client_id"],
            client_secret=settings["github_client_secret"],
            code=code,
            redirect_uri=redirect_uri,
        )
        profile = fetch_github_profile(access_token)
        user = get_or_create_oauth_user(db, profile, provider="github")
        token, refresh_token = _issue_session_tokens(db=db, user=user, request=request)

        return _redirect_to_frontend_success(
            token=token,
            refresh_token=refresh_token,
            email=user.email,
            name=profile["name"],
            username=user.username,
            next_path=next_path,
        )
    except Exception as exc:
        safe_message = user_facing_message(exc, context="GitHub OAuth callback")
        return _redirect_to_frontend_error(safe_message, next_path)


@router.get("/google")
def google_login(
    next: str = Query("/dashboard", alias="next"),
):
    settings = get_oauth_settings()

    if not settings["google_client_id"] or not settings["google_client_secret"]:
        raise HTTPException(
            status_code=503,
            detail="Google sign-in is not configured on the server.",
        )

    next_path = _sanitize_next_path(next)
    state = encode_oauth_state("google", next_path)
    redirect_uri = f"{settings['api_public_url']}/auth/google/callback"

    authorize_url = build_google_authorize_url(
        client_id=settings["google_client_id"],
        redirect_uri=redirect_uri,
        state=state,
    )
    return RedirectResponse(authorize_url, status_code=302)


@router.get("/google/callback")
def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    settings = get_oauth_settings()
    next_path = "/dashboard"

    if error:
        return _redirect_to_frontend_error(f"Google sign-in was cancelled: {error}")

    if not code or not state:
        return _redirect_to_frontend_error("Missing Google authorization response.")

    try:
        state_payload = decode_oauth_state(state)
        next_path = _sanitize_next_path(state_payload.get("next"))
        redirect_uri = f"{settings['api_public_url']}/auth/google/callback"

        access_token = exchange_google_code(
            client_id=settings["google_client_id"],
            client_secret=settings["google_client_secret"],
            code=code,
            redirect_uri=redirect_uri,
        )
        profile = fetch_google_profile(access_token)
        user = get_or_create_oauth_user(db, profile, provider="google")
        token, refresh_token = _issue_session_tokens(db=db, user=user, request=request)

        return _redirect_to_frontend_success(
            token=token,
            refresh_token=refresh_token,
            email=user.email,
            name=profile["name"],
            username=user.username,
            next_path=next_path,
        )
    except Exception as exc:
        safe_message = user_facing_message(exc, context="Google OAuth callback")
        return _redirect_to_frontend_error(safe_message, next_path)
