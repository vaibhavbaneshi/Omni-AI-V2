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

from app.services.memory_summary_service import (
    generate_summary,
    get_summary
)

from app.services.agent_service import (
    retrieval_agent
)

from app.services.tool_agent import (
    tool_calling_agent
)

from app.services.summary_service import (
    summarize_conversation
)

from app.core.security import (
    get_current_user
)

router = APIRouter()

@router.post("/chat")

def chat(
    query: str,
    session_id: int,
    current_user: str = Depends(get_current_user),
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

    generate_summary(
        session_id=session_id
    )

    return result

@router.post("/chat-stream")

def chat_stream(
    query: str,
    session_id: int,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # -----------------------------------
    # SAVE USER MESSAGE
    # -----------------------------------

    save_message(
        db=db,
        session_id=session_id,
        role="user",
        content=query
    )

    # -----------------------------------
    # AGENT
    # -----------------------------------

    agent_result = tool_calling_agent(
        query=query
    )

    print(
        "TOOL USED:",
        agent_result["tool"]
    )

    context = agent_result["context"]

    # -----------------------------------
    # HISTORY
    # -----------------------------------

    history = get_chat_history(
        session_id=session_id
    )

    print(history)

    # -----------------------------------
    # SUMMARY
    # -----------------------------------

    summary = summarize_conversation(
        history
    )

    # -----------------------------------
    # STREAM WRAPPER
    # -----------------------------------

    complete_response = ""

    def generate():

        nonlocal complete_response

        generator = stream_response(
            query=query,
            context=context,
            history=history,
            summary=summary
        )

        for token in generator:

            complete_response += token

            yield token

        # -----------------------------------
        # SAVE ASSISTANT RESPONSE
        # -----------------------------------

        save_message(
            db=db,
            session_id=session_id,
            role="assistant",
            content=complete_response
        )

    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )