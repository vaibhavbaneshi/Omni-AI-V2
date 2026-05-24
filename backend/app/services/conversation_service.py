from app.db.session import SessionLocal

from app.models.message import Message

# -----------------------------------
# GET CHAT HISTORY
# -----------------------------------

def get_chat_history(
    session_id,
    user_id=None,
    limit=5
):

    db = SessionLocal()

    query = (
        db.query(Message)
        .filter(Message.session_id == session_id)
    )

    if user_id is not None:
        query = query.filter(
            Message.user_id == user_id
        )

    messages = (
        query
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
