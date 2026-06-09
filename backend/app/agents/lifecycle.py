"""Agent CRUD and lifecycle — create, pause, resume, delete."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.agents.scheduler import compute_next_run, register_agent_schedule
from app.models.autonomous_agent import AutonomousAgent


def create_agent(
    db: Session,
    *,
    user_id: int,
    name: str,
    agent_type: str,
    workspace_id: str = "default",
    description: str | None = None,
    config: dict[str, Any] | None = None,
    schedule_kind: str = "manual",
    schedule_config: dict[str, Any] | None = None,
    template_id: int | None = None,
) -> AutonomousAgent:
    agent = AutonomousAgent(
        user_id=user_id,
        workspace_id=workspace_id,
        name=name.strip(),
        description=description,
        agent_type=agent_type,
        status="active",
        config=config or {},
        schedule_kind=schedule_kind,
        schedule_config=schedule_config or {},
        template_id=template_id,
    )
    if schedule_kind != "manual":
        agent.next_run_at = compute_next_run(schedule_kind, schedule_config or {})
    db.add(agent)
    db.commit()
    db.refresh(agent)
    register_agent_schedule(db, agent)
    return agent


def list_agents(db: Session, *, user_id: int, limit: int = 100) -> list[AutonomousAgent]:
    return (
        db.query(AutonomousAgent)
        .filter(AutonomousAgent.user_id == user_id)
        .order_by(AutonomousAgent.updated_at.desc())
        .limit(limit)
        .all()
    )


def get_agent(db: Session, *, user_id: int, agent_id: int) -> AutonomousAgent | None:
    return (
        db.query(AutonomousAgent)
        .filter(AutonomousAgent.id == agent_id, AutonomousAgent.user_id == user_id)
        .first()
    )


def update_agent(
    db: Session,
    *,
    user_id: int,
    agent_id: int,
    **fields: Any,
) -> AutonomousAgent | None:
    agent = get_agent(db, user_id=user_id, agent_id=agent_id)
    if not agent:
        return None
    for key, value in fields.items():
        if value is None:
            continue
        if hasattr(agent, key):
            setattr(agent, key, value)
    if "schedule_kind" in fields or "schedule_config" in fields:
        if agent.schedule_kind != "manual":
            agent.next_run_at = compute_next_run(agent.schedule_kind, agent.schedule_config or {})
        else:
            agent.next_run_at = None
    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)
    register_agent_schedule(db, agent)
    return agent


def pause_agent(db: Session, *, user_id: int, agent_id: int) -> AutonomousAgent | None:
    return update_agent(db, user_id=user_id, agent_id=agent_id, status="paused")


def resume_agent(db: Session, *, user_id: int, agent_id: int) -> AutonomousAgent | None:
    agent = update_agent(db, user_id=user_id, agent_id=agent_id, status="active")
    if agent and agent.schedule_kind != "manual" and not agent.next_run_at:
        agent.next_run_at = compute_next_run(agent.schedule_kind, agent.schedule_config or {})
        db.commit()
        db.refresh(agent)
    return agent


def delete_agent(db: Session, *, user_id: int, agent_id: int) -> bool:
    agent = get_agent(db, user_id=user_id, agent_id=agent_id)
    if not agent:
        return False
    db.delete(agent)
    db.commit()
    return True


def serialize_agent(agent: AutonomousAgent) -> dict[str, Any]:
    return {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "agent_type": agent.agent_type,
        "status": agent.status,
        "workspace_id": agent.workspace_id,
        "config": agent.config or {},
        "schedule_kind": agent.schedule_kind,
        "schedule_config": agent.schedule_config or {},
        "next_run_at": agent.next_run_at.isoformat() if agent.next_run_at else None,
        "last_run_at": agent.last_run_at.isoformat() if agent.last_run_at else None,
        "template_id": agent.template_id,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }
