"""GitHub connector API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.app_settings import get_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.github_connector_service import (
    build_connector_authorize_url,
    get_connection,
    handle_connector_callback,
    list_repositories,
    sync_repository,
)

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
    }


@router.get("/authorize")
def github_authorize(
    next: str = Query("/dashboard"),
    current_user: User = Depends(get_current_user),
):
    return RedirectResponse(build_connector_authorize_url(next_path=next), status_code=302)


@router.get("/callback")
def github_connector_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if error:
        raise HTTPException(status_code=400, detail=f"GitHub authorization failed: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing GitHub authorization response.")
    handle_connector_callback(db, user=current_user, code=code, state=state)
    frontend = get_settings().FRONTEND_URL.rstrip("/")
    return RedirectResponse(f"{frontend}/dashboard?github=connected", status_code=302)


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
