import os
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.auth_service import create_access_token
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

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "").strip()
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "").strip()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()


def _sanitize_next_path(next_path: str | None) -> str:
    if not next_path or not next_path.startswith("/"):
        return "/dashboard"
    if next_path.startswith("//"):
        return "/dashboard"
    return next_path


def _frontend_callback_url() -> str:
    return f"{FRONTEND_URL}/auth/callback"


def _redirect_to_frontend_error(message: str, next_path: str = "/login") -> RedirectResponse:
    params = urlencode({"error": message, "next": next_path})
    return RedirectResponse(f"{FRONTEND_URL}/auth/callback?{params}")


def _redirect_to_frontend_success(
    *,
    token: str,
    email: str,
    name: str,
    username: str,
    next_path: str,
) -> RedirectResponse:
    params = urlencode(
        {
            "token": token,
            "email": email,
            "name": name,
            "username": username,
            "next": next_path,
        }
    )
    return RedirectResponse(f"{_frontend_callback_url()}?{params}")


@router.get("/providers")
def oauth_providers():
    return {
        "github": bool(GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET),
        "google": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
    }


@router.get("/github")
def github_login(
    next: str = Query("/dashboard", alias="next"),
):
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="GitHub sign-in is not configured on the server.",
        )

    next_path = _sanitize_next_path(next)
    state = encode_oauth_state("github", next_path)
    redirect_uri = f"{os.getenv('API_PUBLIC_URL', 'http://localhost:8000').rstrip('/')}/auth/github/callback"

    authorize_url = build_github_authorize_url(
        client_id=GITHUB_CLIENT_ID,
        redirect_uri=redirect_uri,
        state=state,
    )
    return RedirectResponse(authorize_url)


@router.get("/github/callback")
def github_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    next_path = "/dashboard"

    if error:
        return _redirect_to_frontend_error(f"GitHub sign-in was cancelled: {error}")

    if not code or not state:
        return _redirect_to_frontend_error("Missing GitHub authorization response.")

    try:
        state_payload = decode_oauth_state(state)
        next_path = _sanitize_next_path(state_payload.get("next"))
        redirect_uri = f"{os.getenv('API_PUBLIC_URL', 'http://localhost:8000').rstrip('/')}/auth/github/callback"

        access_token = exchange_github_code(
            client_id=GITHUB_CLIENT_ID,
            client_secret=GITHUB_CLIENT_SECRET,
            code=code,
            redirect_uri=redirect_uri,
        )
        profile = fetch_github_profile(access_token)
        user = get_or_create_oauth_user(db, profile)
        token = create_access_token(data={"sub": user.username})

        return _redirect_to_frontend_success(
            token=token,
            email=user.email,
            name=profile["name"],
            username=user.username,
            next_path=next_path,
        )
    except Exception as exc:
        return _redirect_to_frontend_error(str(exc), next_path)


@router.get("/google")
def google_login(
    next: str = Query("/dashboard", alias="next"),
):
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Google sign-in is not configured on the server.",
        )

    next_path = _sanitize_next_path(next)
    state = encode_oauth_state("google", next_path)
    redirect_uri = f"{os.getenv('API_PUBLIC_URL', 'http://localhost:8000').rstrip('/')}/auth/google/callback"

    authorize_url = build_google_authorize_url(
        client_id=GOOGLE_CLIENT_ID,
        redirect_uri=redirect_uri,
        state=state,
    )
    return RedirectResponse(authorize_url)


@router.get("/google/callback")
def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    next_path = "/dashboard"

    if error:
        return _redirect_to_frontend_error(f"Google sign-in was cancelled: {error}")

    if not code or not state:
        return _redirect_to_frontend_error("Missing Google authorization response.")

    try:
        state_payload = decode_oauth_state(state)
        next_path = _sanitize_next_path(state_payload.get("next"))
        redirect_uri = f"{os.getenv('API_PUBLIC_URL', 'http://localhost:8000').rstrip('/')}/auth/google/callback"

        access_token = exchange_google_code(
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            code=code,
            redirect_uri=redirect_uri,
        )
        profile = fetch_google_profile(access_token)
        user = get_or_create_oauth_user(db, profile)
        token = create_access_token(data={"sub": user.username})

        return _redirect_to_frontend_success(
            token=token,
            email=user.email,
            name=profile["name"],
            username=user.username,
            next_path=next_path,
        )
    except Exception as exc:
        return _redirect_to_frontend_error(str(exc), next_path)
