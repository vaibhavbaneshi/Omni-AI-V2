"""Knowledge graph API — build, search, and visualize workspace graphs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.app_settings import get_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.knowledge_graph_service import (
    build_workspace_graph,
    get_document_graph,
    get_global_graph,
    search_graph,
)

router = APIRouter(prefix="/graph", tags=["knowledge-graph"])


def _require_knowledge_graph() -> None:
    if not get_settings().ENABLE_KNOWLEDGE_GRAPH:
        raise HTTPException(status_code=403, detail="Knowledge graph is disabled.")


@router.post("/build")
def build_graph(
    workspace_id: str = Query(default="default"),
    document_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_knowledge_graph()
    stats = build_workspace_graph(
        db,
        user_id=current_user.id,
        workspace_id=workspace_id,
        document_id=document_id,
    )
    return {"status": "ok", "workspace_id": workspace_id, **stats}


@router.get("/search")
def graph_search(
    q: str = Query(min_length=1, max_length=512),
    workspace_id: str = Query(default="default"),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_knowledge_graph()
    return search_graph(
        db,
        user_id=current_user.id,
        query=q,
        workspace_id=workspace_id,
        limit=limit,
    )


@router.get("/document/{document_id}")
def document_graph(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_knowledge_graph()
    return get_document_graph(db, user_id=current_user.id, document_id=document_id)


@router.get("/global")
def global_graph(
    workspace_id: str = Query(default="default"),
    limit: int = Query(default=100, ge=1, le=300),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_knowledge_graph()
    return get_global_graph(
        db,
        user_id=current_user.id,
        workspace_id=workspace_id,
        limit=limit,
    )
