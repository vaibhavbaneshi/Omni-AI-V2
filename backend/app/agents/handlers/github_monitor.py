"""GitHub repository monitoring agent."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.agents.memory import add_memory_entry
from app.models.autonomous_agent import AgentExecution, AutonomousAgent
from app.services.github_connector_service import get_connection, sync_repository


def run_github_monitor(
    db: Session,
    *,
    agent: AutonomousAgent,
    execution: AgentExecution,
) -> dict[str, Any]:
    config = agent.config or {}
    repo = config.get("repo_full_name")
    if not repo:
        raise ValueError("github_monitor agent requires config.repo_full_name")

    connection = get_connection(db, user_id=agent.user_id)
    if not connection:
        raise ValueError("GitHub is not connected. Connect via /connectors first.")

    from app.models.user import User

    user = db.query(User).filter(User.id == agent.user_id).first()
    if not user:
        raise ValueError("User not found.")

    result = sync_repository(
        db,
        user=user,
        repo_full_name=repo,
        workspace_id=agent.workspace_id,
        session_id=config.get("session_id"),
    )
    summary = f"GitHub sync {result.get('status')}: {repo} ({result.get('files_indexed', 0)} files)"
    add_memory_entry(
        db,
        agent_id=agent.id,
        execution_id=execution.id,
        memory_type="observation",
        content=summary,
        metadata=result,
    )
    return {"summary": summary, **result}
