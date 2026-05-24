from sqlalchemy.orm import Session

from app.agent.orchestrator import AgentOrchestrator


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
