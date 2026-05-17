from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.oauth_config import get_oauth_settings, oauth_providers_status
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
    email: str,
    name: str,
    username: str,
    next_path: str,
) -> RedirectResponse:
    settings = get_oauth_settings()
    params = urlencode(
        {
            "token": token,
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


@router.get("/providers")
def oauth_providers():
    return oauth_providers_status()


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
