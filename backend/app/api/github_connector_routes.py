"""GitHub connector API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.app_settings import get_settings
from app.core.oauth_config import get_oauth_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.github_connector_service import (
    build_connector_authorize_url,
    connect_github_account_from_token,
    get_connection,
    list_repositories,
    sync_repository,
)
from app.services.oauth_service import decode_oauth_state, exchange_github_code

router = APIRouter(prefix="/connectors/github", tags=["connectors", "github"])


class GitHubSyncRequest(BaseModel):
    repo_full_name: str = Field(min_length=3, max_length=256)
    workspace_id: str = "default"
    session_id: int | None = None


@router.get("/status")
def github_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    connection = get_connection(db, user_id=current_user.id)
    return {
        "connected": connection is not None,
        "github_login": connection.github_login if connection else None,
        "signed_in_with_github": current_user.oauth_provider == "github",
    }


@router.get("/authorize-url")
def github_authorize_url(
    next: str = Query("/chat"),
    current_user: User = Depends(get_current_user),
):
    return {
        "authorize_url": build_connector_authorize_url(
            user_id=current_user.id,
            next_path=next,
        )
    }


@router.get("/authorize")
def github_authorize(
    request: Request,
    next: str = Query("/chat"),
    current_user: User = Depends(get_current_user),
):
    authorize_url = build_connector_authorize_url(user_id=current_user.id, next_path=next)
    if "application/json" in (request.headers.get("accept") or "").lower():
        return {"authorize_url": authorize_url}
    return RedirectResponse(authorize_url, status_code=302)


@router.get("/callback")
def github_connector_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    """Legacy callback for GitHub apps that still register /connectors/github/callback."""
    frontend = get_settings().FRONTEND_URL.rstrip("/")

    if error:
        return RedirectResponse(
            f"{frontend}/chat?github_error={error}",
            status_code=302,
        )
    if not code or not state:
        return RedirectResponse(
            f"{frontend}/chat?github_error=missing_authorization",
            status_code=302,
        )

    try:
        state_payload = decode_oauth_state(state)
        user_id = state_payload.get("user_id")
        if not user_id:
            raise ValueError("Missing user in connector state")
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise ValueError("User not found")

        settings = get_oauth_settings()
        legacy_redirect_uri = f"{settings['api_public_url']}/connectors/github/callback"
        access_token = exchange_github_code(
            client_id=settings["github_client_id"],
            client_secret=settings["github_client_secret"],
            code=code,
            redirect_uri=legacy_redirect_uri,
        )
        connect_github_account_from_token(db, user=user, access_token=access_token)
        next_path = state_payload.get("next") or "/chat"
        if not next_path.startswith("/"):
            next_path = "/chat"
        return RedirectResponse(f"{frontend}{next_path}?github=connected", status_code=302)
    except Exception:
        return RedirectResponse(f"{frontend}/chat?github_error=authorization_failed", status_code=302)


@router.get("/repos")
def github_repos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"repositories": list_repositories(db, user_id=current_user.id)}


@router.post("/sync")
def github_sync(
    body: GitHubSyncRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return sync_repository(
            db,
            user=current_user,
            repo_full_name=body.repo_full_name,
            workspace_id=body.workspace_id,
            session_id=body.session_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
