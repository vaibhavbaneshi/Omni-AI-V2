"""Test-only auth helpers — enabled when TEST_MODE=true."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.cookie_auth import set_auth_cookies
from app.core.app_settings import get_settings
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expires_at,
)
from app.services.settings_service import ensure_user_settings, register_user_session

router = APIRouter(prefix="/auth", tags=["auth", "test"])

TEST_USER_EMAIL = "test@omni.local"
TEST_USER_USERNAME = "test_omni"


def _test_mode_enabled() -> bool:
    return os.environ.get("TEST_MODE", "").strip().lower() in {"1", "true", "yes"}


def _get_or_create_test_user(db: Session) -> User:
    user = db.query(User).filter(User.email == TEST_USER_EMAIL).first()
    if user:
        ensure_user_settings(db, user)
        return user
    user = User(
        username=TEST_USER_USERNAME,
        email=TEST_USER_EMAIL,
        password=hash_password("test-mode-not-for-production"),
        oauth_provider="test",
        has_password=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    ensure_user_settings(db, user)
    return user


@router.post("/test-session")
def create_test_session(
    request: Request,
    db: Session = Depends(get_db),
):
    if not _test_mode_enabled():
        raise HTTPException(status_code=404, detail="Not found.")
    user = _get_or_create_test_user(db)
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
        ip_address="127.0.0.1",
    )
    body = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "email": user.email,
        "username": user.username,
        "name": user.username,
    }
    response = JSONResponse(body)
    if get_settings().AUTH_COOKIE_ENABLED:
        set_auth_cookies(response, access_token=access_token, refresh_token=refresh_token)
    return response
