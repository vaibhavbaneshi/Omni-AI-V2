"""Chat folder CRUD and session organization."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.chat_folder import ChatFolder
from app.models.chat_session import ChatSession


def list_folders(
    db: Session,
    *,
    user_id: int,
    workspace_id: str = "default",
) -> list[dict]:
    folders = (
        db.query(ChatFolder)
        .filter(
            ChatFolder.user_id == user_id,
            ChatFolder.workspace_id == workspace_id,
        )
        .order_by(ChatFolder.name.asc())
        .all()
    )

    results: list[dict] = []
    for folder in folders:
        session_count = (
            db.query(ChatSession)
            .filter(
                ChatSession.user_id == user_id,
                ChatSession.folder_id == folder.id,
            )
            .count()
        )
        results.append(
            {
                "id": folder.id,
                "name": folder.name,
                "workspace_id": folder.workspace_id,
                "session_count": session_count,
                "created_at": folder.created_at.isoformat() if folder.created_at else None,
            }
        )
    return results


def create_folder(
    db: Session,
    *,
    user_id: int,
    name: str,
    workspace_id: str = "default",
) -> ChatFolder:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Folder name is required.")

    existing = (
        db.query(ChatFolder)
        .filter(
            ChatFolder.user_id == user_id,
            ChatFolder.workspace_id == workspace_id,
            ChatFolder.name == cleaned,
        )
        .first()
    )
    if existing:
        return existing

    folder = ChatFolder(user_id=user_id, workspace_id=workspace_id, name=cleaned)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


def update_folder(
    db: Session,
    *,
    user_id: int,
    folder_id: int,
    name: str,
) -> ChatFolder | None:
    folder = (
        db.query(ChatFolder)
        .filter(
            ChatFolder.id == folder_id,
            ChatFolder.user_id == user_id,
        )
        .first()
    )
    if not folder:
        return None

    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Folder name is required.")

    folder.name = cleaned
    db.commit()
    db.refresh(folder)
    return folder


def delete_folder(
    db: Session,
    *,
    user_id: int,
    folder_id: int,
) -> bool:
    folder = (
        db.query(ChatFolder)
        .filter(
            ChatFolder.id == folder_id,
            ChatFolder.user_id == user_id,
        )
        .first()
    )
    if not folder:
        return False

    (
        db.query(ChatSession)
        .filter(
            ChatSession.user_id == user_id,
            ChatSession.folder_id == folder.id,
        )
        .update({ChatSession.folder_id: None}, synchronize_session=False)
    )
    db.delete(folder)
    db.commit()
    return True


def get_owned_folder(
    db: Session,
    *,
    user_id: int,
    folder_id: int,
) -> ChatFolder | None:
    return (
        db.query(ChatFolder)
        .filter(
            ChatFolder.id == folder_id,
            ChatFolder.user_id == user_id,
        )
        .first()
    )


def update_session_organization(
    db: Session,
    *,
    user_id: int,
    session_id: int,
    is_pinned: bool | None = None,
    folder_id: int | None = None,
    clear_folder: bool = False,
) -> ChatSession | None:
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        )
        .first()
    )
    if not session:
        return None

    if is_pinned is not None:
        session.is_pinned = is_pinned

    if clear_folder:
        session.folder_id = None
    elif folder_id is not None:
        folder = get_owned_folder(db, user_id=user_id, folder_id=folder_id)
        if not folder:
            raise ValueError("Folder not found.")
        session.folder_id = folder.id

    db.commit()
    db.refresh(session)
    return session


def session_to_list_item(session: ChatSession, *, folder_name: str | None = None) -> dict:
    return {
        "id": session.id,
        "title": session.title,
        "is_pinned": bool(session.is_pinned),
        "folder_id": session.folder_id,
        "folder_name": folder_name,
        "workspace_id": session.workspace_id,
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }
