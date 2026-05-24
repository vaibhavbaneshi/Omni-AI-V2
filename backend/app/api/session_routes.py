from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.db.session import get_db

from app.models.chat_session import (
    ChatSession
)

from app.services.title_service import (
    generate_chat_title
)

from app.models.message import Message

from app.core.security import get_current_user

from app.models.user import User

router = APIRouter()

@router.post("/sessions/create")

def create_session(
    first_message: str,
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

@router.post("/sessions")
def create_session(
    title: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    session = ChatSession(
        title=title,
        user_id=current_user.id
    )

    db.add(session)

    db.commit()

    db.refresh(session)

    return {
        "id": session.id,
        "title": session.title
    }
