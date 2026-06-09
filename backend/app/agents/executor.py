"""Execute autonomous agents and persist runs + memory."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.agents.memory import add_memory_entry
from app.agents.registry import get_agent_handler
from app.agents.scheduler import compute_next_run, register_agent_schedule
from app.models.autonomous_agent import AgentExecution, AutonomousAgent
from app.services.notification_service import notify_user

logger = logging.getLogger(__name__)


def execute_agent(
    db: Session,
    *,
    agent_id: int,
    user_id: int | None = None,
    trigger: str = "manual",
) -> AgentExecution:
    agent = db.query(AutonomousAgent).filter(AutonomousAgent.id == agent_id).first()
    if not agent:
        raise ValueError(f"Agent {agent_id} not found.")
    if user_id is not None and agent.user_id != user_id:
        raise ValueError("Agent access denied.")
    if agent.status == "paused":
        raise ValueError("Agent is paused.")

    execution = AgentExecution(
        agent_id=agent.id,
        user_id=agent.user_id,
        status="running",
        trigger=trigger,
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    started = time.perf_counter()
    try:
        handler = get_agent_handler(agent.agent_type)
        result = handler(db, agent=agent, execution=execution)
        execution.status = "complete"
        execution.output = result
        execution.tokens_used = int(result.get("tokens_used") or 0)
        execution.cost_usd = result.get("cost_usd")
        add_memory_entry(
            db,
            agent_id=agent.id,
            execution_id=execution.id,
            memory_type="output",
            content=str(result.get("summary") or result.get("message") or "Run complete"),
            metadata=result,
        )
        notify_user(
            db,
            user_id=agent.user_id,
            title=f"Agent '{agent.name}' completed",
            body=result.get("summary") or "Execution finished successfully.",
            category="agent",
            link=f"/agents?agent={agent.id}",
        )
    except Exception as exc:
        execution.status = "failed"
        execution.error_message = str(exc)[:2000]
        logger.exception("Agent execution failed agent_id=%s", agent.id)
        notify_user(
            db,
            user_id=agent.user_id,
            title=f"Agent '{agent.name}' failed",
            body=str(exc)[:500],
            category="agent",
            link=f"/agents?agent={agent.id}",
        )
        raise
    finally:
        execution.latency_ms = int((time.perf_counter() - started) * 1000)
        execution.finished_at = datetime.utcnow()
        agent.last_run_at = execution.finished_at
        if agent.schedule_kind != "manual":
            agent.next_run_at = compute_next_run(agent.schedule_kind, agent.schedule_config or {})
        db.commit()
        db.refresh(execution)
        register_agent_schedule(db, agent)

    return execution


def list_executions(
    db: Session,
    *,
    user_id: int,
    agent_id: int | None = None,
    limit: int = 50,
) -> list[AgentExecution]:
    query = db.query(AgentExecution).filter(AgentExecution.user_id == user_id)
    if agent_id is not None:
        query = query.filter(AgentExecution.agent_id == agent_id)
    return query.order_by(AgentExecution.started_at.desc()).limit(limit).all()


def serialize_execution(row: AgentExecution) -> dict[str, Any]:
    return {
        "id": row.id,
        "agent_id": row.agent_id,
        "status": row.status,
        "trigger": row.trigger,
        "output": row.output,
        "error_message": row.error_message,
        "tokens_used": row.tokens_used,
        "latency_ms": row.latency_ms,
        "cost_usd": row.cost_usd,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
    }
