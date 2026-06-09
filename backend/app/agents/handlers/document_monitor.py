"""Document monitoring agent — stale embeddings and re-index detection."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.agents.memory import add_memory_entry
from app.models.autonomous_agent import AgentExecution, AutonomousAgent
from app.models.document import DocumentRecord


def run_document_monitor(
    db: Session,
    *,
    agent: AutonomousAgent,
    execution: AgentExecution,
) -> dict[str, Any]:
    config = agent.config or {}
    stale_days = int(config.get("stale_days") or 14)
    cutoff = datetime.utcnow() - timedelta(days=stale_days)

    query = db.query(DocumentRecord).filter(DocumentRecord.user_id == agent.user_id)
    if agent.workspace_id:
        query = query.filter(DocumentRecord.workspace_id == agent.workspace_id)

    documents = query.all()
    stale = []
    needs_reindex = []

    for doc in documents:
        updated = doc.indexing_updated_at or doc.created_at
        if updated and updated < cutoff and doc.indexing_stage == "complete":
            stale.append({"id": doc.id, "filename": doc.filename})
        if doc.indexing_stage in {"failed", "queued"} or (doc.chunks_created or 0) == 0:
            needs_reindex.append({"id": doc.id, "filename": doc.filename, "stage": doc.indexing_stage})

    observation = (
        f"Scanned {len(documents)} documents. "
        f"{len(stale)} stale, {len(needs_reindex)} need re-indexing."
    )
    add_memory_entry(
        db,
        agent_id=agent.id,
        execution_id=execution.id,
        memory_type="observation",
        content=observation,
        metadata={"stale": stale, "needs_reindex": needs_reindex},
    )

    return {
        "summary": observation,
        "stale_count": len(stale),
        "reindex_count": len(needs_reindex),
        "stale_documents": stale[:20],
        "needs_reindex": needs_reindex[:20],
    }
