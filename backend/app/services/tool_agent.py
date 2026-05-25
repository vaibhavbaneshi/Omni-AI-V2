from sqlalchemy.orm import Session

from app.agent.orchestrator import AgentOrchestrator
from app.core.app_settings import get_settings
from app.services.research_workflow import run_deep_research


orchestrator = AgentOrchestrator()


def tool_calling_agent(
    query: str,
    user_id: int,
    db: Session,
    mode: str = "research",
    workspace_id: str = "default",
    collection_id: int | None = None,
    session_id: int | None = None,
    history: str = ""
):
    settings = get_settings()
    deep_research_requested = (
        mode in {"deep-research", "analyst"}
        or "deep research" in query.lower()
    )
    if settings.ENABLE_DEEP_RESEARCH and deep_research_requested:
        return run_deep_research(
            query=query,
            user_id=user_id,
            db=db,
            workspace_id=workspace_id,
            collection_id=collection_id,
        )

    bundle = orchestrator.run(
        query=query,
        user_id=user_id,
        db=db,
        mode=mode,
        workspace_id=workspace_id,
        collection_id=collection_id,
        session_id=session_id,
        history=history
    )

    meta = bundle.to_meta()

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
        "metadata": meta["metadata"]
    }
