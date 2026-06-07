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


def get_active_worker_count() -> int:
    """Return number of RQ workers connected to Redis, or -1 if Redis is unreachable."""
    try:
        from rq.worker import Worker

        conn = get_redis_connection()
        return len(Worker.all(connection=conn))
    except Exception as exc:
        logger.warning("[INGEST_WORKER_CHECK_FAILED] error=%s", exc)
        return -1


def get_ingest_job_info(job_id: str) -> dict | None:
    """Fetch RQ job metadata for operator / stale diagnostics."""
    try:
        job = Job.fetch(job_id, connection=get_redis_connection())
    except Exception:
        return None
    return {
        "job_id": job.id,
        "status": job.get_status(),
        "enqueued_at": job.enqueued_at.isoformat() if job.enqueued_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "origin": job.origin,
        "description": job.description,
    }


def build_stale_queued_message(document: DocumentRecord, elapsed_seconds: int) -> str:
    """Human-readable stall reason with queue/worker context for status polling."""
    if not ingest_queue_enabled():
        return (
            f"Indexing stuck at 'queued' for {elapsed_seconds}s. "
            "The in-process background task may not have started — check API logs for [INGEST_TASK_START]."
        )

    worker_count = get_active_worker_count()
    try:
        metrics = get_ingestion_queue_metrics()
    except Exception as exc:
        metrics = {"queue_length": "?", "active_jobs": "?", "failed_jobs": "?"}
        logger.warning("[INGEST_METRICS_FAILED] error=%s", exc)

    job_info = get_ingest_job_info(document.indexing_job_id) if document.indexing_job_id else None

    parts = [f"Indexing stuck at 'queued' for {elapsed_seconds}s."]
    if worker_count == 0:
        parts.append(
            "No RQ ingestion workers are connected to Redis — the API enqueued the job but nothing is "
            "processing it. On Railway, run API + worker in one service "
            "(default Dockerfile CMD uses scripts/railway_web_and_worker.sh)."
        )
    elif worker_count < 0:
        parts.append("Could not reach Redis to check workers — verify REDIS_URL.")
    else:
        parts.append(
            f"{worker_count} worker(s) connected but this job has not started "
            f"(queue_length={metrics.get('queue_length')}, active_jobs={metrics.get('active_jobs')})."
        )

    if job_info:
        parts.append(
            f"job_id={job_info['job_id']} job_status={job_info['status']}."
        )
    if metrics.get("failed_jobs"):
        parts.append(f"failed_jobs={metrics['failed_jobs']} — check GET /admin/ingestion-queue/metrics.")

    return " ".join(parts)


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

    worker_count = get_active_worker_count()
    if worker_count == 0:
        logger.error(
            "[INGEST_NO_WORKER] job_id=%s document_id=%s queue=%s — job enqueued but no RQ workers "
            "are connected to Redis; indexing will stay queued until a worker starts",
            job.id,
            document_id,
            INGEST_QUEUE_NAME,
        )
    elif worker_count < 0:
        logger.warning(
            "[INGEST_WORKER_UNKNOWN] job_id=%s document_id=%s — could not verify worker count",
            job.id,
            document_id,
        )
    else:
        logger.info(
            "[INGEST_WORKERS_OK] job_id=%s document_id=%s worker_count=%s",
            job.id,
            document_id,
            worker_count,
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
        "[INGEST_RQ_ENQUEUED] job_id=%s document_id=%s queue=%s max_retries=%s worker_count=%s",
        job.id,
        document_id,
        INGEST_QUEUE_NAME,
        settings.INGEST_JOB_MAX_RETRIES,
        worker_count,
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
    worker_count = get_active_worker_count()

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
        "worker_count": worker_count,
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
