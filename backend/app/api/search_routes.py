"""Global workspace search API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.workspace_schemas import SearchResponse
from app.services.search_service import global_search

router = APIRouter(tags=["workspace-search"])


@router.get("/search", response_model=SearchResponse)
def search_workspace(
    q: str = Query(min_length=2, max_length=500),
    workspace_id: str = "default",
    limit: int = Query(default=20, ge=1, le=50),
    types: str | None = Query(
        default=None,
        description="Comma-separated result types: session,message,document,insight",
    ),
    source: str | None = Query(default=None, description="Filter documents by connector collection source name"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    allowed = None
    if types:
        allowed = {item.strip() for item in types.split(",") if item.strip()}

    payload = global_search(
        db,
        user_id=current_user.id,
        query=q,
        workspace_id=workspace_id,
        limit=limit,
        types=allowed,
        source=source,
    )
    return payload
