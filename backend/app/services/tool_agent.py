from sqlalchemy.orm import Session

from app.agent.document_analysis_agent import (
    run_document_analysis_agent,
    should_run_document_analysis_agent,
)
from app.agent.orchestrator import AgentOrchestrator
from app.agent.research_agent import run_research_agent
from app.core.app_settings import get_settings
from app.services.attachment_service import (
    NO_DOCUMENT_MESSAGE,
    is_document_query,
    session_has_documents,
)


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


def _merge_agent_fields(result: dict) -> dict:
    metadata = result.get("metadata") or {}
    return {
        **result,
        "agent": result.get("agent") or metadata.get("agent"),
        "report_id": result.get("report_id") or metadata.get("report_id"),
        "document_analysis": result.get("document_analysis") or metadata.get("documents"),
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

    if settings.ENABLE_AGENT_WORKFLOWS and should_run_document_analysis_agent(
        db,
        query=query,
        user_id=user_id,
        session_id=session_id,
        workspace_id=workspace_id,
    ):
        return _merge_agent_fields(
            run_document_analysis_agent(
                query=query,
                user_id=user_id,
                db=db,
                workspace_id=workspace_id,
                session_id=session_id,
            )
        )

    deep_research_requested = (
        mode in {"deep-research", "analyst"}
        or "deep research" in query.lower()
    )
    if settings.ENABLE_DEEP_RESEARCH and deep_research_requested and not document_query:
        try:
            return _merge_agent_fields(
                run_research_agent(
                    query=query,
                    user_id=user_id,
                    db=db,
                    workspace_id=workspace_id,
                    collection_id=collection_id,
                    session_id=session_id,
                    history=history,
                )
            )
        except Exception as exc:
            return _refusal_result(
                strategy="research-agent",
                message=f"Research agent failed: {exc}",
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
        "retrieval_query": meta["metadata"].get("retrieval_query"),
        "original_query": meta["metadata"].get("original_query"),
        "multi_document": meta["metadata"].get("multi_document", False),
    }
