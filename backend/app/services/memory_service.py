from sqlalchemy.orm.session import Session

from app.models.message import Message

# -----------------------------------
# SAVE MESSAGE
# -----------------------------------

def save_message(
    db: Session,
    session_id: int,
    role: str,
    content: str
):

    message = Message(
        session_id=session_id,
        role=role,
        content=content
    )

    db.add(message)

    db.commit()

    db.refresh(message)

    return message

# -----------------------------------
# GET CHAT HISTORY
# -----------------------------------

def get_chat_history(
    db: Session,
    session_id: int
):

    messages = db.query(Message).filter(
        Message.session_id == session_id
    ).all()

    return messages