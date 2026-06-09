"""Redis + RQ queue for durable document ingestion."""

from __future__ import annotations

import logging
import os
import re
import threading
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

_inline_recovery_lock = threading.Lock()
_inline_recovery_started: set[int] = set()


def _retry_policy() -> Retry:
    settings = get_settings()
    intervals = settings.ingest_job_retry_intervals
    return Retry(max=settings.INGEST_JOB_MAX_RETRIES, interval=intervals)


LEGACY_FIXED_WORKER_NAME = "omniai-ingest-worker"


def resolve_ingest_worker_name() -> str:
    """Unique RQ worker name per container/process (avoids Railway restart collisions)."""
    settings = get_settings()
    configured = (settings.INGEST_WORKER_NAME or "").strip()
    if configured:
        return configured

    ident = (
        os.environ.get("RAILWAY_REPLICA_ID")
        or os.environ.get("RAILWAY_DEPLOYMENT_ID")
        or os.environ.get("HOSTNAME")
        or "local"
    )
    safe_ident = re.sub(r"[^A-Za-z0-9_-]+", "-", ident).strip("-") or "local"
    return f"omniai-ingest-{safe_ident}-{os.getpid()}"


def cleanup_legacy_ingest_worker_registrations(conn) -> None:
    """Remove stale fixed-name worker keys left by older deployments."""
    try:
        from rq.worker import Worker
    except ImportError:
        return

    try:
        for worker in Worker.all(connection=conn):
            if worker.name != LEGACY_FIXED_WORKER_NAME:
                continue
            logger.warning(
                "Removing legacy RQ worker registration name=%s pid=%s",
                worker.name,
                getattr(worker, "pid", None),
            )
            worker.register_death()
    except Exception:
        logger.exception("Failed to clean up legacy ingest worker registrations")


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
        "status": str(job.get_status()),
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
    if document.indexing_error:
        parts.append(f"Last error: {document.indexing_error}")
    elif metrics.get("failed_jobs"):
        parts.append(
            f"{metrics['failed_jobs']} job(s) failed recently — often HF_TOKEN/auth. "
            "Check Railway logs for [EMBEDDING_AUTH_ERROR] or 401 Unauthorized."
        )
    if worker_count == 0:
        parts.append(
            "No RQ workers connected — ingestion should auto-fallback to the API process; "
            "if this persists, redeploy with the default Dockerfile CMD (railway_web_and_worker.sh)."
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

    return " ".join(parts)


def run_ingest_inline_thread(document_id: int, *, db: Session | None = None) -> None:
    """Run ingestion inside the API container when RQ workers are unavailable."""
    from app.services.ingestion_service import run_ingest_document_record

    if db is not None:
        update_indexing_progress(db, document_id, stage="queued", mark_started=True)

    def _run() -> None:
        run_ingest_document_record(document_id, job_id=f"inline-{document_id}")

    threading.Thread(
        target=_run,
        name=f"ingest-inline-{document_id}",
        daemon=True,
    ).start()
    logger.info("[INGEST_INLINE_START] document_id=%s pid=%s", document_id, __import__("os").getpid())


def try_recover_stuck_queued_document(document_id: int) -> bool:
    """One-shot recovery for documents stuck in Redis while no worker is connected."""
    if get_active_worker_count() != 0:
        return False
    with _inline_recovery_lock:
        if document_id in _inline_recovery_started:
            return False
        _inline_recovery_started.add(document_id)
    logger.warning(
        "[INGEST_INLINE_RECOVERY] document_id=%s — no RQ workers, starting in-process ingest",
        document_id,
    )
    run_ingest_inline_thread(document_id)
    return True


def dispatch_document_ingestion(db: Session, document_id: int) -> dict:
    """Enqueue to RQ when a worker is connected; otherwise ingest in-process."""
    return dispatch_documents_ingestion(db, [document_id])


def dispatch_documents_ingestion(db: Session, document_ids: list[int]) -> dict:
    """Enqueue many documents with minimal DB round-trips."""
    unique_ids = [doc_id for doc_id in dict.fromkeys(document_ids) if doc_id]
    if not unique_ids:
        return {"dispatch": "none", "queued": 0, "worker_count": 0}

    worker_count = get_active_worker_count()
    if worker_count > 0:
        queued = enqueue_documents_ingestion(db, unique_ids)
        return {
            "dispatch": "rq",
            "queued": queued,
            "worker_count": worker_count,
        }

    logger.warning(
        "[INGEST_FALLBACK_INLINE] document_count=%s worker_count=%s — skipping RQ, using API process",
        len(unique_ids),
        worker_count,
    )
    for document_id in unique_ids[:5]:
        run_ingest_inline_thread(document_id, db=db)
    return {
        "dispatch": "inline_thread",
        "queued": min(len(unique_ids), 5),
        "worker_count": worker_count,
        "warning": (
            "No RQ worker connected — indexing runs in the API process instead of the queue. "
            "Check deploy logs for [worker-supervisor]."
        ),
    }


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


def enqueue_documents_ingestion(db: Session, document_ids: list[int]) -> int:
    """Enqueue many ingestion jobs and persist queue metadata in one DB commit."""
    if not document_ids:
        return 0

    settings = get_settings()
    queue = get_ingest_queue()
    retry = _retry_policy()
    documents = {
        row.id: row
        for row in db.query(DocumentRecord)
        .filter(DocumentRecord.id.in_(document_ids))
        .all()
    }
    queued = 0
    base_ts = int(time.time())

    for index, document_id in enumerate(document_ids):
        job = queue.enqueue(
            INGEST_JOB_PATH,
            document_id,
            job_id=f"ingest-doc-{document_id}-{base_ts}-{index}",
            retry=retry,
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
        document = documents.get(document_id)
        if document:
            document.indexing_job_id = job.id
        queued += 1

    db.commit()
    logger.info(
        "[INGEST_RQ_ENQUEUED_BATCH] queued=%s queue=%s max_retries=%s",
        queued,
        INGEST_QUEUE_NAME,
        settings.INGEST_JOB_MAX_RETRIES,
    )
    return queued


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
