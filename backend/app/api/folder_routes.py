"""Chat folder API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.workspace_schemas import (
    ChatFolderCreate,
    ChatFolderResponse,
    ChatFolderUpdate,
)
from app.services.folder_service import (
    create_folder,
    delete_folder,
    list_folders,
    update_folder,
)

router = APIRouter(prefix="/folders", tags=["workspace-folders"])


@router.get("", response_model=list[ChatFolderResponse])
def read_folders(
    workspace_id: str = "default",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_folders(db, user_id=current_user.id, workspace_id=workspace_id)


@router.post("", response_model=ChatFolderResponse)
def create_folder_route(
    body: ChatFolderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        folder = create_folder(
            db,
            user_id=current_user.id,
            name=body.name,
            workspace_id=body.workspace_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    items = list_folders(db, user_id=current_user.id, workspace_id=body.workspace_id)
    match = next((item for item in items if item["id"] == folder.id), None)
    return match or {
        "id": folder.id,
        "name": folder.name,
        "workspace_id": folder.workspace_id,
        "session_count": 0,
        "created_at": folder.created_at.isoformat() if folder.created_at else None,
    }


@router.patch("/{folder_id}", response_model=ChatFolderResponse)
def update_folder_route(
    folder_id: int,
    body: ChatFolderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        folder = update_folder(
            db,
            user_id=current_user.id,
            folder_id=folder_id,
            name=body.name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found.")

    items = list_folders(db, user_id=current_user.id, workspace_id=folder.workspace_id)
    match = next((item for item in items if item["id"] == folder.id), None)
    return match or {
        "id": folder.id,
        "name": folder.name,
        "workspace_id": folder.workspace_id,
        "session_count": 0,
        "created_at": folder.created_at.isoformat() if folder.created_at else None,
    }


@router.delete("/{folder_id}")
def delete_folder_route(
    folder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deleted = delete_folder(db, user_id=current_user.id, folder_id=folder_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Folder not found.")
    return {"message": "Folder deleted", "folder_id": folder_id}
