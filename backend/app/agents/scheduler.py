"""Schedule computation and RQ registration for autonomous agents."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models.autonomous_agent import AutonomousAgent

logger = logging.getLogger(__name__)


def compute_next_run(schedule_kind: str, schedule_config: dict[str, Any]) -> datetime:
    now = datetime.utcnow()
    hour = int(schedule_config.get("hour", 9))
    minute = int(schedule_config.get("minute", 0))

    if schedule_kind == "hourly":
        return now + timedelta(hours=1)
    if schedule_kind == "daily":
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate
    if schedule_kind == "weekly":
        day = int(schedule_config.get("day_of_week", 0))
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        days_ahead = (day - candidate.weekday()) % 7
        candidate += timedelta(days=days_ahead or 7)
        if candidate <= now:
            candidate += timedelta(days=7)
        return candidate
    return now + timedelta(days=1)


def register_agent_schedule(db: Session, agent: AutonomousAgent) -> None:
    """Enqueue next run via RQ when Redis is available."""
    if agent.status != "active" or agent.schedule_kind == "manual" or not agent.next_run_at:
        return
    try:
        from app.services.agent_scheduler_service import enqueue_agent_run

        enqueue_agent_run(agent.id, run_at=agent.next_run_at)
    except Exception:
        logger.exception("Failed to register schedule for agent_id=%s", agent.id)


def agents_due_for_run(db: Session, *, now: datetime | None = None) -> list[AutonomousAgent]:
    now = now or datetime.utcnow()
    return (
        db.query(AutonomousAgent)
        .filter(
            AutonomousAgent.status == "active",
            AutonomousAgent.schedule_kind != "manual",
            AutonomousAgent.next_run_at.isnot(None),
            AutonomousAgent.next_run_at <= now,
        )
        .all()
    )
