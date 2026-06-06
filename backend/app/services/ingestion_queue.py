"""Redis + RQ queue for durable document ingestion."""

from __future__ import annotations

import logging
import time

from rq import Queue, Retry
from rq.job import Job
from rq.registry import FailedJobRegistry, FinishedJobRegistry, StartedJobRegistry
from sqlalchemy.orm import Session

from app.core.app_settings import get_settings
from app.core.redis_client import get_redis_connection
from app.models.document import DocumentRecord
from app.services.indexing_progress import mark_indexing_failed, update_indexing_progress

logger = logging.getLogger("omniai.ingestion.queue")

INGEST_QUEUE_NAME = "ingest"
INGEST_DLQ_NAME = "ingest-dlq"
INGEST_JOB_PATH = "app.jobs.ingestion_jobs.execute_ingestion_job"
DLQ_JOB_PATH = "app.jobs.ingestion_jobs.record_dead_letter"
JOB_TIMEOUT_SECONDS = 1800  # 30 minutes — large PDFs + cold HF embeddings


def _retry_policy() -> Retry:
    settings = get_settings()
    intervals = settings.ingest_job_retry_intervals
    return Retry(max=settings.INGEST_JOB_MAX_RETRIES, interval=intervals)


def get_ingest_queue() -> Queue:
    return Queue(INGEST_QUEUE_NAME, connection=get_redis_connection())


def get_dlq() -> Queue:
    return Queue(INGEST_DLQ_NAME, connection=get_redis_connection())


def ingest_queue_enabled() -> bool:
    settings = get_settings()
    return settings.INGEST_IN_BACKGROUND and settings.ingest_uses_rq_queue


def should_use_background_tasks() -> bool:
    settings = get_settings()
    return settings.INGEST_IN_BACKGROUND and not settings.ingest_uses_rq_queue


def on_ingestion_job_failure(job, connection, exc_type, exc_value, traceback) -> None:
    """RQ failure hook — DLQ + mark failed only after retries are exhausted."""
    document_id = job.args[0] if job.args else None
    failure_reason = str(exc_value) if exc_value else exc_type.__name__
    duration_ms = None
    if job.started_at and job.ended_at:
        duration_ms = round((job.ended_at - job.started_at).total_seconds() * 1000, 2)

    retries_left = getattr(job, "retries_left", 0) or 0
    if retries_left > 0:
        logger.warning(
            "[INGEST_JOB_RETRY_SCHEDULED] job_id=%s document_id=%s retries_left=%s failure_reason=%s",
            job.id,
            document_id,
            retries_left,
            failure_reason,
        )
        return

    logger.error(
        "[INGEST_JOB_EXHAUSTED] job_id=%s document_id=%s duration_ms=%s failure_reason=%s",
        job.id,
        document_id,
        duration_ms,
        failure_reason,
    )

    dlq = Queue(INGEST_DLQ_NAME, connection=connection)
    dlq.enqueue(
        DLQ_JOB_PATH,
        job.id,
        document_id,
        failure_reason,
        duration_ms,
        job_timeout=120,
    )

    if document_id is not None:
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            mark_indexing_failed(
                db,
                document_id,
                f"Ingestion failed after {get_settings().INGEST_JOB_MAX_RETRIES} retries: {failure_reason}",
            )
        finally:
            db.close()


def enqueue_document_ingestion(db: Session, document_id: int) -> str:
    """Enqueue ingestion job; persist job id on document record."""
    settings = get_settings()
    queue = get_ingest_queue()
    job_id = f"ingest-doc-{document_id}-{int(time.time())}"

    job = queue.enqueue(
        INGEST_JOB_PATH,
        document_id,
        job_id=job_id,
        retry=_retry_policy(),
        job_timeout=JOB_TIMEOUT_SECONDS,
        result_ttl=settings.INGEST_JOB_RESULT_TTL_SECONDS,
        failure_ttl=settings.INGEST_JOB_FAILURE_TTL_SECONDS,
        on_failure=on_ingestion_job_failure,
        description=f"Index document {document_id}",
    )

    update_indexing_progress(
        db,
        document_id,
        stage="queued",
        mark_started=True,
    )
    document = db.query(DocumentRecord).filter(DocumentRecord.id == document_id).first()
    if document:
        document.indexing_job_id = job.id
        db.commit()

    logger.info(
        "[INGEST_RQ_ENQUEUED] job_id=%s document_id=%s queue=%s max_retries=%s",
        job.id,
        document_id,
        INGEST_QUEUE_NAME,
        settings.INGEST_JOB_MAX_RETRIES,
    )
    return job.id


def get_ingestion_queue_metrics() -> dict:
    """Operational metrics for monitoring dashboards."""
    conn = get_redis_connection()
    queue = get_ingest_queue()
    dlq = get_dlq()

    started = StartedJobRegistry(queue=queue)
    failed = FailedJobRegistry(queue=queue)
    finished = FinishedJobRegistry(queue=queue)

    return {
        "queue_name": INGEST_QUEUE_NAME,
        "dlq_name": INGEST_DLQ_NAME,
        "queue_length": queue.count,
        "dlq_length": dlq.count,
        "active_jobs": started.count,
        "failed_jobs": failed.count,
        "completed_jobs": finished.count,
        "deferred_jobs": queue.deferred_job_registry.count,
        "scheduled_jobs": queue.scheduled_job_registry.count,
    }


def list_recent_dlq_jobs(limit: int = 20) -> list[dict]:
    dlq = get_dlq()
    jobs: list[dict] = []
    for job_id in dlq.job_ids[:limit]:
        try:
            job = Job.fetch(job_id, connection=get_redis_connection())
        except Exception:
            continue
        jobs.append(
            {
                "job_id": job.id,
                "document_id": job.args[1] if len(job.args) > 1 else None,
                "failure_reason": job.args[2] if len(job.args) > 2 else job.description,
                "enqueued_at": job.enqueued_at.isoformat() if job.enqueued_at else None,
            }
        )
    return jobs


def requeue_failed_job(job_id: str) -> str:
    """Re-enqueue a failed ingestion job (operator recovery)."""
    conn = get_redis_connection()
    job = Job.fetch(job_id, connection=conn)
    document_id = job.args[0]
    queue = get_ingest_queue()
    new_job = queue.enqueue(
        INGEST_JOB_PATH,
        document_id,
        retry=_retry_policy(),
        job_timeout=JOB_TIMEOUT_SECONDS,
        on_failure=on_ingestion_job_failure,
        description=f"Requeued index document {document_id}",
    )
    logger.info(
        "[INGEST_JOB_REQUEUED] old_job_id=%s new_job_id=%s document_id=%s",
        job_id,
        new_job.id,
        document_id,
    )
    return new_job.id
