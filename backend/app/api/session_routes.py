from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from sqlalchemy.orm import Session

from app.db.session import get_db

from app.models.chat_session import (
    ChatSession
)

from app.services.title_service import (
    generate_chat_title,
    refine_chat_title,
)
from app.services.session_service import DeleteSessionResult, delete_chat_session

from app.models.message import Message

from app.core.security import get_current_user

from app.models.user import User

router = APIRouter()

@router.post("/sessions/create")

def create_session(
    first_message: Annotated[str, Query(min_length=1, max_length=12_000)],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    title = generate_chat_title(
        first_message
    )

    new_session = ChatSession(
        title=title,
        user_id=current_user.id
    )

    db.add(new_session)

    db.commit()

    db.refresh(new_session)

    return {
        "id": new_session.id,
        "session_id": new_session.id,
        "title": new_session.title
    }

@router.get("/sessions")

def get_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.id.desc())
        .all()
    )

    return [
        {
            "id": session.id,
            "title": session.title
        }
        for session in sessions
    ]

# -----------------------------------
# GET SESSION MESSAGES
# -----------------------------------

@router.get("/sessions/{session_id}/messages")

def get_session_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        )
        .first()
    )

    if not session:
        return []

    messages = (
        db.query(Message)
        .filter(
            Message.session_id == session_id,
            Message.user_id == current_user.id
        )
        .order_by(Message.id.asc())
        .all()
    )

    return [
        {
            "id": message.id,
            "session_id": message.session_id,
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at.isoformat() if message.created_at else None
        }
        for message in messages
    ]

@router.patch("/sessions/{session_id}")
def update_session(
    session_id: int,
    title: Annotated[str, Query(min_length=1, max_length=120)],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
        .first()
    )

    if not session:
        return {"error": "Session not found"}

    cleaned = title.strip()[:120] or session.title
    session.title = cleaned
    db.commit()
    db.refresh(session)

    return {"id": session.id, "title": session.title}


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = delete_chat_session(
        db,
        user_id=current_user.id,
        session_id=session_id,
    )
    if result is DeleteSessionResult.NOT_FOUND:
        raise HTTPException(status_code=404, detail="Session not found")
    if result is DeleteSessionResult.FAILED:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete session. Please try again.",
        )
    return {"message": "Session deleted", "session_id": session_id}


@router.post("/sessions/{session_id}/title/refine")
def refine_session_title(
    session_id: int,
    first_message: Annotated[str, Query(min_length=1, max_length=12_000)],
    assistant_preview: Annotated[str, Query(max_length=2_000)] = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
        .first()
    )

    if not session:
        return {"error": "Session not found"}

    title = refine_chat_title(first_message, assistant_preview)
    session.title = title
    db.commit()
    db.refresh(session)

    return {"id": session.id, "title": session.title}


@router.post("/sessions")
def create_session_with_title(
    title: Annotated[str, Query(min_length=1, max_length=120)] = "New Chat",
    first_message: Annotated[str | None, Query(max_length=12_000)] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resolved_title = title.strip() or "New Chat"
    if first_message and first_message.strip():
        resolved_title = generate_chat_title(first_message.strip())

    session = ChatSession(
        title=resolved_title,
        user_id=current_user.id,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "id": session.id,
        "title": session.title,
    }
