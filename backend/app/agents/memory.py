"""Agent memory — goals, plans, observations, outputs."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.autonomous_agent import AgentMemoryEntry


def add_memory_entry(
    db: Session,
    *,
    agent_id: int,
    memory_type: str,
    content: str,
    execution_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> AgentMemoryEntry:
    entry = AgentMemoryEntry(
        agent_id=agent_id,
        execution_id=execution_id,
        memory_type=memory_type,
        content=content,
        metadata=metadata,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_memory_entries(
    db: Session,
    *,
    agent_id: int,
    memory_type: str | None = None,
    limit: int = 100,
) -> list[AgentMemoryEntry]:
    query = db.query(AgentMemoryEntry).filter(AgentMemoryEntry.agent_id == agent_id)
    if memory_type:
        query = query.filter(AgentMemoryEntry.memory_type == memory_type)
    return query.order_by(AgentMemoryEntry.created_at.desc()).limit(limit).all()


def serialize_memory(entry: AgentMemoryEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "agent_id": entry.agent_id,
        "execution_id": entry.execution_id,
        "memory_type": entry.memory_type,
        "content": entry.content,
        "metadata": entry.memory_metadata,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }
