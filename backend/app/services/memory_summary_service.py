from app.db.session import SessionLocal

from app.models.message import Message

from app.models.conversation_summary import (
    ConversationSummary
)   

# -----------------------------------
# GENERATE SUMMARY
# -----------------------------------

def generate_summary(
    session_id
):

    db = SessionLocal()

    messages = (
        db.query(Message)
        .filter(
            Message.session_id == session_id
        )
        .all()
    )

    summary = ""

    for msg in messages:

        summary += (
            f"{msg.role}: {msg.content}\n"
        )

    summary = summary[-2000:]

    existing = (
        db.query(ConversationSummary)
        .filter(
            ConversationSummary.session_id
            == session_id
        )
        .first()
    )

    if existing:

        existing.summary = summary

    else:

        new_summary = ConversationSummary(
            session_id=session_id,
            summary=summary
        )

        db.add(new_summary)

    db.commit()

    db.close()

def get_summary(
    session_id
):

    db = SessionLocal()

    summary = (
        db.query(ConversationSummary)
        .filter(
            ConversationSummary.session_id
            == session_id
        )
        .first()
    )

    db.close()

    if summary:

        return summary.summary

    return ""