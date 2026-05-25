from app.db.database import (
    engine,
    Base
)

from app.models.chat_session import (
    ChatSession
)

from app.models.message import (
    Message
)

from app.models.user import User

from app.models.document import (
    DocumentCollection,
    DocumentRecord
)

from app.models.memory import UserMemory
from app.models.conversation_summary import ConversationSummary

def init_db():

    Base.metadata.create_all(
        bind=engine
    )

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
