from fastapi import APIRouter, Depends, Request
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

from app.services.title_service import refine_chat_title, should_refine_session_title
from app.services.attachment_service import is_document_query
from app.core.security import get_current_user
from app.core.app_settings import get_settings
from app.core.sanitize import sanitize_user_query
from app.core.telemetry import get_trace_id, set_trace_context
from app.core.llm import LLMProviderError
from app.core.safe_errors import chat_facing_message
from app.services.model_router import get_provider_for_route, resolve_model_route
from app.models.user import User
from app.models.chat_session import ChatSession
from app.models.message import Message

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

STREAM_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.post("/chat-stream")
async def chat_stream(
    request: Request,
    query: str,
    session_id: int,
    mode: str = "research",
    model: str | None = None,
    workspace_id: str = "default",
    collection_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    set_trace_context(trace_id=get_trace_id(), user_id=current_user.id)
    query = sanitize_user_query(query, max_length=get_settings().MAX_QUERY_CHARS)

    try:
        model_route = resolve_model_route(mode=mode, query=query, model_id=model)
        llm_provider = get_provider_for_route(model_route)
    except LLMProviderError as exc:
        def model_error():
            yield json.dumps(
                {"type": "error", "message": chat_facing_message(exc, context="model routing")}
            ) + "\n"
            yield json.dumps({"type": "done"}) + "\n"

        return StreamingResponse(
            model_error(),
            media_type="application/x-ndjson",
            status_code=400,
            headers=STREAM_HEADERS,
        )

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
            status_code=404,
            headers=STREAM_HEADERS,
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
    cancelled = False

    async def generate():
        nonlocal complete_response, cancelled

        yield json.dumps(
            {
                "type": "status",
                "phase": "routing",
                "message": "Planning agent route",
            }
        ) + "\n"

        if await request.is_disconnected():
            cancelled = True
            yield json.dumps({"type": "cancelled", "message": "Client disconnected"}) + "\n"
            return

        try:
            summary = summarize_conversation(history) if history else ""
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
            history=history,
        )

        if await request.is_disconnected():
            cancelled = True
            yield json.dumps({"type": "cancelled", "message": "Client disconnected"}) + "\n"
            return

        refusal = agent_result.get("refusal")
        context = agent_result["context"]
        sources = agent_result.get("sources", [])
        tool_used = agent_result.get("tool", "rag")
        strategy = agent_result.get("strategy", tool_used)
        route = agent_result.get("route", {})
        workspace_mode = agent_result.get("mode", mode)
        document_summary = is_document_query(query) and bool((context or "").strip())
        require_grounding = is_document_query(query) and not document_summary

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
                    "summary": bool(summary),
                },
                "model": model_route.to_dict(),
            }
        ) + "\n"

        if refusal:
            complete_response = refusal
            yield json.dumps({"type": "token", "content": refusal}) + "\n"
            save_message(
                db=db,
                session_id=session_id,
                role="assistant",
                content=complete_response,
                user_id=current_user.id,
            )
            try:
                generate_summary(session_id=session_id)
            except Exception:
                pass
            yield json.dumps({"type": "done"}) + "\n"
            return

        try:
            generator = stream_response(
                query=query,
                context=context,
                history=history,
                summary=summary,
                mode=workspace_mode,
                route=route,
                require_grounding=require_grounding,
                document_summary=document_summary,
                user_id=current_user.id,
                session_id=session_id,
                provider=llm_provider,
            )

            for token in generator:
                if await request.is_disconnected():
                    cancelled = True
                    yield json.dumps({"type": "cancelled", "message": "Generation stopped"}) + "\n"
                    return

                complete_response += token
                yield json.dumps({"type": "token", "content": token}) + "\n"
        except Exception as exc:
            yield json.dumps(
                {"type": "error", "message": chat_facing_message(exc, context="chat stream")}
            ) + "\n"
            yield json.dumps({"type": "done"}) + "\n"
            return

        if complete_response and not cancelled:
            save_message(
                db=db,
                session_id=session_id,
                role="assistant",
                content=complete_response,
                user_id=current_user.id,
            )

            try:
                generate_summary(session_id=session_id)
            except Exception:
                pass

            try:
                assistant_count = (
                    db.query(Message)
                    .filter(
                        Message.session_id == session_id,
                        Message.role == "assistant",
                    )
                    .count()
                )
                session_record = (
                    db.query(ChatSession)
                    .filter(
                        ChatSession.id == session_id,
                        ChatSession.user_id == current_user.id,
                    )
                    .first()
                )
                if (
                    session_record
                    and should_refine_session_title(
                        session_record.title,
                        assistant_message_count=assistant_count,
                    )
                ):
                    refined_title = refine_chat_title(query, complete_response[:400])
                    session_record.title = refined_title
                    db.commit()
                    yield json.dumps(
                        {
                            "type": "title",
                            "session_id": session_id,
                            "title": refined_title,
                        }
                    ) + "\n"
            except Exception:
                pass

        yield json.dumps({"type": "done"}) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers=STREAM_HEADERS,
    )
