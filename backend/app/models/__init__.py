from app.models.conversation_summary import (
    ConversationSummary
)

from app.db.database import (
    engine,
    Base
)

# IMPORT ALL MODELS HERE

from app.models.user import User
from app.models.chat_session import ChatSession
from app.models.message import Message

def init_db():

    Base.metadata.create_all(
        bind=engine
    )

if __name__ == "__main__":

    init_db()

    print("Database initialized.")