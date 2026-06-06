"""RQ job functions for durable document ingestion."""

from __future__ import annotations

import logging
import os
import time

from rq import get_current_job

from app.services.ingestion_service import ingest_document_record

logger = logging.getLogger("omniai.ingestion.jobs")


def execute_ingestion_job(document_id: int) -> dict:
    """Run full ingestion pipeline inside an RQ worker.

    Must remain a top-level importable function for RQ serialization.
    """
    job = get_current_job()
    job_id = job.id if job else None
    started = time.perf_counter()

    logger.info(
        "[INGEST_JOB_START] job_id=%s document_id=%s pid=%s worker=%s",
        job_id,
        document_id,
        os.getpid(),
        os.environ.get("HOSTNAME", "local"),
    )

    try:
        ingest_document_record(document_id, job_id=job_id, propagate_errors=True)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "[INGEST_JOB_COMPLETE] job_id=%s document_id=%s duration_ms=%s",
            job_id,
            document_id,
            duration_ms,
        )
        return {
            "job_id": job_id,
            "document_id": document_id,
            "duration_ms": duration_ms,
            "status": "completed",
        }
    except Exception as exc:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.exception(
            "[INGEST_JOB_FAILED] job_id=%s document_id=%s duration_ms=%s failure_reason=%s",
            job_id,
            document_id,
            duration_ms,
            exc,
        )
        raise


def record_dead_letter(
    source_job_id: str,
    document_id: int | None,
    failure_reason: str,
    duration_ms: float | None = None,
) -> dict:
    """Persist dead-letter metadata on the DLQ queue for operator review."""
    logger.error(
        "[INGEST_DLQ] job_id=%s document_id=%s duration_ms=%s failure_reason=%s",
        source_job_id,
        document_id,
        duration_ms,
        failure_reason,
    )
    return {
        "source_job_id": source_job_id,
        "document_id": document_id,
        "failure_reason": failure_reason[:4000],
        "duration_ms": duration_ms,
    }
