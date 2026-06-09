"""Autonomous agent workspace API — Phase M."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.executor import execute_agent, list_executions, serialize_execution
from app.agents.lifecycle import (
    create_agent,
    delete_agent,
    get_agent,
    list_agents,
    pause_agent,
    resume_agent,
    serialize_agent,
    update_agent,
)
from app.agents.memory import list_memory_entries, serialize_memory
from app.agents.registry import list_agent_types
from app.core.app_settings import get_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.agent_scheduler_service import enqueue_agent_run_now

router = APIRouter(prefix="/agents/workspace", tags=["agents", "workspace"])


class AgentCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    agent_type: str
    description: str | None = None
    workspace_id: str = "default"
    config: dict = Field(default_factory=dict)
    schedule_kind: str = "manual"
    schedule_config: dict = Field(default_factory=dict)
    template_id: int | None = None


class AgentUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    config: dict | None = None
    schedule_kind: str | None = None
    schedule_config: dict | None = None


def _require_agents() -> None:
    if not get_settings().ENABLE_AUTONOMOUS_AGENTS:
        raise HTTPException(status_code=403, detail="Autonomous agents are disabled.")


@router.get("/types")
def agent_types(current_user: User = Depends(get_current_user)):
    _require_agents()
    return {"types": list_agent_types()}


@router.get("")
def list_user_agents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_agents()
    return {"agents": [serialize_agent(row) for row in list_agents(db, user_id=current_user.id)]}


@router.post("")
def create_user_agent(
    body: AgentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_agents()
    agent = create_agent(
        db,
        user_id=current_user.id,
        name=body.name,
        agent_type=body.agent_type,
        description=body.description,
        workspace_id=body.workspace_id,
        config=body.config,
        schedule_kind=body.schedule_kind,
        schedule_config=body.schedule_config,
        template_id=body.template_id,
    )
    return serialize_agent(agent)


@router.get("/{agent_id}")
def read_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_agents()
    agent = get_agent(db, user_id=current_user.id, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return serialize_agent(agent)


@router.patch("/{agent_id}")
def patch_agent(
    agent_id: int,
    body: AgentUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_agents()
    agent = update_agent(db, user_id=current_user.id, agent_id=agent_id, **body.model_dump(exclude_unset=True))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return serialize_agent(agent)


@router.post("/{agent_id}/pause")
def pause_user_agent(agent_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_agents()
    agent = pause_agent(db, user_id=current_user.id, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return serialize_agent(agent)


@router.post("/{agent_id}/resume")
def resume_user_agent(agent_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_agents()
    agent = resume_agent(db, user_id=current_user.id, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return serialize_agent(agent)


@router.delete("/{agent_id}")
def remove_agent(agent_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_agents()
    if not delete_agent(db, user_id=current_user.id, agent_id=agent_id):
        raise HTTPException(status_code=404, detail="Agent not found.")
    return {"deleted": True}


@router.post("/{agent_id}/run")
def run_agent_now(agent_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_agents()
    agent = get_agent(db, user_id=current_user.id, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")
    job_id = enqueue_agent_run_now(agent_id)
    if job_id:
        return {"queued": True, "job_id": job_id}
    execution = execute_agent(db, agent_id=agent_id, user_id=current_user.id, trigger="manual")
    return {"queued": False, "execution": serialize_execution(execution)}


@router.get("/{agent_id}/executions")
def agent_executions(
    agent_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_agents()
    if not get_agent(db, user_id=current_user.id, agent_id=agent_id):
        raise HTTPException(status_code=404, detail="Agent not found.")
    rows = list_executions(db, user_id=current_user.id, agent_id=agent_id, limit=limit)
    return {"executions": [serialize_execution(row) for row in rows]}


@router.get("/{agent_id}/memory")
def agent_memory(
    agent_id: int,
    memory_type: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_agents()
    if not get_agent(db, user_id=current_user.id, agent_id=agent_id):
        raise HTTPException(status_code=404, detail="Agent not found.")
    rows = list_memory_entries(db, agent_id=agent_id, memory_type=memory_type)
    return {"memory": [serialize_memory(row) for row in rows]}
