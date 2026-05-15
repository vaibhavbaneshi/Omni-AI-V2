from app.db.session import SessionLocal

from app.models.message import Message

# -----------------------------------
# GET CHAT HISTORY
# -----------------------------------

def get_chat_history(
    session_id,
    limit=5
):

    db = SessionLocal()

    messages = (
        db.query(Message)
        .filter(
            Message.session_id == session_id
        )
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )

    db.close()

    messages.reverse()

    history = ""

    for msg in messages:

        history += (
            f"{msg.role}: {msg.content}\n"
        )

    return history