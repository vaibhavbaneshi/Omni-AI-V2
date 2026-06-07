"""Multi-step autonomous research workflow (delegates to ResearchAgent)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agent.research_agent import run_research_agent


def run_deep_research(
    *,
    query: str,
    user_id: int,
    db: Session,
    workspace_id: str = "default",
    collection_id: int | None = None,
    session_id: int | None = None,
    history: str = "",
    max_iterations: int = 3,
) -> dict:
    """Backward-compatible entry point for deep research mode."""
    return run_research_agent(
        query=query,
        user_id=user_id,
        db=db,
        workspace_id=workspace_id,
        collection_id=collection_id,
        session_id=session_id,
        history=history,
        max_iterations=max_iterations,
    )
