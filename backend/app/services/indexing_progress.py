"""Persist ingestion stage/progress to PostgreSQL for polling clients."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.document import DocumentRecord


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def update_indexing_progress(
    db: Session,
    document_id: int,
    *,
    stage: str | None = None,
    chunks_created: int | None = None,
    embeddings_completed: int | None = None,
    error: str | None = None,
    mark_started: bool = False,
) -> None:
    document = db.query(DocumentRecord).filter(DocumentRecord.id == document_id).first()
    if not document:
        return

    now = _utcnow()
    if mark_started and document.indexing_started_at is None:
        document.indexing_started_at = now

    if stage is not None:
        document.indexing_stage = stage
    if chunks_created is not None:
        document.chunks_created = chunks_created
    if embeddings_completed is not None:
        document.embeddings_completed = embeddings_completed
    if error is not None:
        document.indexing_error = error[:4000] if error else None

    document.indexing_updated_at = now
    db.commit()


def mark_indexing_failed(db: Session, document_id: int, error: str) -> None:
    update_indexing_progress(
        db,
        document_id,
        stage="failed",
        error=error,
    )


def mark_indexing_ready(db: Session, document_id: int, chunk_count: int) -> None:
    update_indexing_progress(
        db,
        document_id,
        stage="ready",
        chunks_created=chunk_count,
        embeddings_completed=chunk_count,
        error="",
    )


def document_status_payload(document: DocumentRecord) -> dict:
    stage = document.indexing_stage or ("ready" if document.chunks_created > 0 else "queued")
    if document.chunks_created > 0 and stage not in {"failed"}:
        stage = "ready"

    total_chunks = document.chunks_created if document.chunks_created > 0 else None
    embeddings_done = document.embeddings_completed or 0

    status = "ready" if stage == "ready" or document.chunks_created > 0 else "indexing"
    if stage == "failed":
        status = "failed"

    elapsed_seconds = None
    if document.indexing_started_at:
        elapsed_seconds = round(
            (_utcnow() - document.indexing_started_at).total_seconds(),
            1,
        )

    return {
        "id": document.id,
        "filename": document.filename,
        "chunks_created": document.chunks_created,
        "embeddings_completed": embeddings_done,
        "indexing_stage": stage,
        "indexing_error": document.indexing_error,
        "indexing_started_at": document.indexing_started_at.isoformat()
        if document.indexing_started_at
        else None,
        "indexing_updated_at": document.indexing_updated_at.isoformat()
        if document.indexing_updated_at
        else None,
        "elapsed_seconds": elapsed_seconds,
        "status": status,
    }
