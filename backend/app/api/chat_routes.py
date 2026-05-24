from fastapi import APIRouter
from fastapi import Depends
import json

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
from app.models.user import User
from app.models.chat_session import ChatSession

router = APIRouter()

@router.post("/chat")

def chat(
    query: str,
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
        return {
            "error": "Session not found"
        }

    # SAVE USER MESSAGE

    save_message(
        db=db,
        session_id=session_id,
        role="user",
        content=query,
        user_id=current_user.id
    )

    # GENERATE AI RESPONSE

    result = chat_with_rag(query)

    # SAVE AI RESPONSE

    save_message(
        db=db,
        session_id=session_id,
        role="assistant",
        content=result["response"],
        user_id=current_user.id
    )

    generate_summary(
        session_id=session_id
    )

    return result

@router.post("/chat-stream")

def chat_stream(
    query: str,
    session_id: int,
    mode: str = "research",
    workspace_id: str = "default",
    collection_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
        def not_found():
            yield json.dumps(
                {
                    "type": "error",
                    "message": "Session not found"
                }
            ) + "\n"

        return StreamingResponse(
            not_found(),
            media_type="application/x-ndjson",
            status_code=404
        )

    # -----------------------------------
    # SAVE USER MESSAGE
    # -----------------------------------

    save_message(
        db=db,
        session_id=session_id,
        role="user",
        content=query,
        user_id=current_user.id
    )

    # -----------------------------------
    # HISTORY
    # -----------------------------------

    history = get_chat_history(
        session_id=session_id,
        user_id=current_user.id
    )

    # -----------------------------------
    # STREAM WRAPPER
    # -----------------------------------

    complete_response = ""

    def generate():

        nonlocal complete_response

        yield json.dumps(
            {
                "type": "status",
                "phase": "routing",
                "message": "Planning agent route"
            }
        ) + "\n"

        try:
            summary = summarize_conversation(
                history
            ) if history else ""
        except Exception:
            summary = ""

        agent_result = tool_calling_agent(
            query=query,
            user_id=current_user.id,
            db=db,
            mode=mode,
            workspace_id=workspace_id,
            collection_id=collection_id,
            session_id=session_id,
            history=history
        )

        context = agent_result["context"]
        sources = agent_result.get("sources", [])
        tool_used = agent_result.get("tool", "rag")
        strategy = agent_result.get("strategy", tool_used)
        route = agent_result.get("route", {})
        workspace_mode = agent_result.get("mode", mode)

        yield json.dumps(
            {
                "type": "meta",
                "tool": tool_used,
                "strategy": strategy,
                "mode": workspace_mode,
                "route": route,
                "sources": sources,
                "source_groups": agent_result.get("source_groups", {}),
                "tools": agent_result.get("tools", []),
                "traces": agent_result.get("traces", []),
                "memory": {
                    "conversation_history": bool(history),
                    "summary": bool(summary)
                }
            }
        ) + "\n"

        generator = stream_response(
            query=query,
            context=context,
            history=history,
            summary=summary,
            mode=workspace_mode,
            route=route
        )

        for token in generator:

            complete_response += token

            yield json.dumps(
                {
                    "type": "token",
                    "content": token
                }
            ) + "\n"

        # -----------------------------------
        # SAVE ASSISTANT RESPONSE
        # -----------------------------------

        save_message(
            db=db,
            session_id=session_id,
            role="assistant",
            content=complete_response,
            user_id=current_user.id
        )

        yield json.dumps(
            {
                "type": "done"
            }
        ) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson"
    )
