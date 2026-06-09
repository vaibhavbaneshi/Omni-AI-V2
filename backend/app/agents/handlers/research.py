"""Scheduled research agent handler."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.agents.memory import add_memory_entry
from app.models.autonomous_agent import AgentExecution, AutonomousAgent
from app.research.pipeline import run_deep_research


def run_scheduled_research(
    db: Session,
    *,
    agent: AutonomousAgent,
    execution: AgentExecution,
) -> dict[str, Any]:
    config = agent.config or {}
    query = config.get("query") or agent.description or agent.name
    add_memory_entry(
        db,
        agent_id=agent.id,
        execution_id=execution.id,
        memory_type="goal",
        content=query,
    )
    result = run_deep_research(
        db,
        query=query,
        user_id=agent.user_id,
        workspace_id=agent.workspace_id,
        collection_id=config.get("collection_id"),
        session_id=config.get("session_id"),
        max_iterations=int(config.get("max_iterations") or 3),
    )
    add_memory_entry(
        db,
        agent_id=agent.id,
        execution_id=execution.id,
        memory_type="observation",
        content=result.get("report", {}).get("executive_summary") or "Research completed.",
        metadata={"report_id": result.get("report_id")},
    )
    return {
        "summary": result.get("report", {}).get("executive_summary") or "Research completed.",
        "report_id": result.get("report_id"),
        "tokens_used": result.get("tokens_used", 0),
        "cost_usd": result.get("cost_usd"),
    }
