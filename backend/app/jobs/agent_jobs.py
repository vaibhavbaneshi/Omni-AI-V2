"""RQ job entrypoint for autonomous agent execution."""

from __future__ import annotations

import logging

from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def run_agent_job(agent_id: int) -> dict:
    from app.agents.executor import execute_agent

    db = SessionLocal()
    try:
        execution = execute_agent(db, agent_id=agent_id, trigger="scheduled")
        return {"execution_id": execution.id, "status": execution.status}
    finally:
        db.close()


def poll_due_agents() -> int:
    """Fallback poller when RQ scheduler is unavailable."""
    from datetime import datetime

    from app.agents.scheduler import agents_due_for_run
    from app.agents.executor import execute_agent

    db = SessionLocal()
    count = 0
    try:
        for agent in agents_due_for_run(db, now=datetime.utcnow()):
            try:
                execute_agent(db, agent_id=agent.id, trigger="scheduled")
                count += 1
            except Exception:
                logger.exception("Scheduled agent run failed agent_id=%s", agent.id)
    finally:
        db.close()
    return count
