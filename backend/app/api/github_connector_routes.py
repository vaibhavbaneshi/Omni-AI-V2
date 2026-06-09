"""GitHub connector API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.app_settings import get_settings
from app.core.oauth_config import get_oauth_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.github_connector import GitHubRepositorySync
from app.models.user import User
from app.services.github_connector_service import (
    build_connector_authorize_url,
    connect_github_account_from_token,
    get_connection,
    list_repositories,
    run_github_sync_job,
)
from app.services.oauth_service import decode_oauth_state, exchange_github_code

router = APIRouter(prefix="/connectors/github", tags=["connectors", "github"])
logger = logging.getLogger(__name__)


class GitHubSyncRequest(BaseModel):
    repo_full_name: str = Field(min_length=3, max_length=256)
    workspace_id: str = "default"


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
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    connection = get_connection(db, user_id=current_user.id)
    if not connection:
        raise HTTPException(
            status_code=400,
            detail="GitHub is not connected. Authorize the connector first.",
        )

    sync = (
        db.query(GitHubRepositorySync)
        .filter(
            GitHubRepositorySync.user_id == current_user.id,
            GitHubRepositorySync.repo_full_name == body.repo_full_name,
        )
        .first()
    )
    if sync and sync.sync_status == "running":
        return {
            "status": "running",
            "message": "Sync already in progress for this repository.",
            "files_indexed": sync.files_indexed,
        }

    if sync is None:
        sync = GitHubRepositorySync(
            user_id=current_user.id,
            connection_id=connection.id,
            repo_full_name=body.repo_full_name,
            default_branch="main",
            workspace_id=body.workspace_id,
        )
        db.add(sync)
    sync.sync_status = "running"
    sync.sync_metadata = None
    db.commit()

    background_tasks.add_task(
        run_github_sync_job,
        user_id=current_user.id,
        repo_full_name=body.repo_full_name,
        workspace_id=body.workspace_id,
    )
    return {
        "status": "running",
        "message": "Sync started. Files will appear in the GitHub collection shortly.",
        "files_indexed": sync.files_indexed,
    }
