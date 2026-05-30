from sqlalchemy.orm import Session

from app.agent.orchestrator import AgentOrchestrator
from app.core.app_settings import get_settings
from app.services.attachment_service import (
    NO_DOCUMENT_MESSAGE,
    is_document_query,
    session_has_documents,
)
from app.services.research_workflow import run_deep_research


orchestrator = AgentOrchestrator()


def _refusal_result(*, strategy: str, message: str) -> dict:
    return {
        "tool": strategy,
        "strategy": strategy,
        "context": "",
        "sources": [],
        "route": {
            "strategy": strategy,
            "tools": [],
            "reason": message,
            "status": "refused",
        },
        "mode": "research",
        "source_groups": {},
        "tools": [],
        "traces": [],
        "metadata": {"refusal": True},
        "refusal": message,
    }


def tool_calling_agent(
    query: str,
    user_id: int,
    db: Session,
    mode: str = "research",
    workspace_id: str = "default",
    collection_id: int | None = None,
    session_id: int | None = None,
    history: str = "",
):
    settings = get_settings()
    document_query = is_document_query(query)
    has_docs = session_has_documents(
        db,
        user_id=user_id,
        session_id=session_id,
        workspace_id=workspace_id,
    )

    if document_query and not has_docs:
        return _refusal_result(strategy="document-retrieval", message=NO_DOCUMENT_MESSAGE)

    deep_research_requested = (
        mode in {"deep-research", "analyst"}
        or "deep research" in query.lower()
    )
    if settings.ENABLE_DEEP_RESEARCH and deep_research_requested and not document_query:
        return run_deep_research(
            query=query,
            user_id=user_id,
            db=db,
            workspace_id=workspace_id,
            collection_id=collection_id,
            session_id=session_id,
        )

    bundle = orchestrator.run(
        query=query,
        user_id=user_id,
        db=db,
        mode=mode,
        workspace_id=workspace_id,
        collection_id=collection_id,
        session_id=session_id,
        history=history,
    )

    meta = bundle.to_meta()
    document_sources = meta.get("source_groups", {}).get("documents", [])
    has_retrieval_context = bool((bundle.context or "").strip())
    has_document_evidence = bool(document_sources) or has_retrieval_context

    if document_query and not has_document_evidence:
        return _refusal_result(
            strategy=bundle.route.strategy,
            message=NO_DOCUMENT_MESSAGE,
        )

    return {
        "tool": bundle.route.strategy,
        "context": bundle.context,
        "sources": meta["sources"],
        "strategy": bundle.route.strategy,
        "route": meta["route"],
        "mode": mode,
        "source_groups": meta["source_groups"],
        "tools": meta["tools"],
        "traces": meta["traces"],
        "metadata": meta["metadata"],
    }
