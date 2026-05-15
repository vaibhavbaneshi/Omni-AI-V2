from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.db.session import get_db

from app.services.rag_service import (
    chat_with_rag
)

from app.services.memory_service import (
    save_message
)

from fastapi.responses import (
    StreamingResponse
)

from app.services.rag_service import (
    retrieve_context,
    stream_response
)

from app.services.conversation_service import (
    get_chat_history
)

router = APIRouter()

@router.post("/chat")

def chat(
    query: str,
    session_id: int,
    db: Session = Depends(get_db)
):

    # SAVE USER MESSAGE

    save_message(
        db=db,
        session_id=session_id,
        role="user",
        content=query
    )

    # GENERATE AI RESPONSE

    result = chat_with_rag(query)

    # SAVE AI RESPONSE

    save_message(
        db=db,
        session_id=session_id,
        role="assistant",
        content=result["response"]
    )

    return result

@router.post("/chat-stream")

def chat_stream(
    query: str,
    session_id: int
):

    context = retrieve_context(query)

    history = get_chat_history( 
        session_id=session_id
    )   

    generator = stream_response(
        query=query,
        context=context,
        history=history
    )

    return StreamingResponse(
        generator,
        media_type="text/plain"
    )