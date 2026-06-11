#!/usr/bin/env python
"""RQ worker process for durable document ingestion.

Usage:
    cd backend && python -m app.worker

Production (Railway / Docker):
    python -m app.worker
"""

from __future__ import annotations

import logging
import os
import sys

import app.core.chroma_client  # noqa: F401 — silence Chroma telemetry before worker imports

from app.core.logging_config import setup_logging
from app.services.ingestion_queue import (
    INGEST_DLQ_NAME,
    INGEST_QUEUE_NAME,
    cleanup_legacy_ingest_worker_registrations,
    resolve_ingest_worker_name,
)

setup_logging()
logger = logging.getLogger("omniai.worker")


def main() -> int:
    from rq import Queue, Worker

    from app.core.app_settings import get_settings
    from app.core.redis_client import get_redis_connection
    from app.jobs.agent_jobs import ensure_agent_poll_scheduled
    from app.services.agent_scheduler_service import AGENT_QUEUE_NAME

    settings = get_settings()
    settings.validate_for_runtime()

    worker_name = resolve_ingest_worker_name()

    logger.info(
        "Starting ingestion worker name=%s queues=%s,%s embedding_provider=%s redis=%s pid=%s",
        worker_name,
        INGEST_QUEUE_NAME,
        INGEST_DLQ_NAME,
        settings.EMBEDDING_PROVIDER,
        settings.redis_url.split("@")[-1] if settings.redis_url else "unset",
        os.getpid(),
    )

    conn = get_redis_connection()
    cleanup_legacy_ingest_worker_registrations(conn)
    queues = [
        Queue(INGEST_QUEUE_NAME, connection=conn),
        Queue(INGEST_DLQ_NAME, connection=conn),
        Queue(AGENT_QUEUE_NAME, connection=conn),
    ]
    # Autonomous agent scheduling requires Redis — poll_due_agents runs every 60s via RQ.
    ensure_agent_poll_scheduled()
    worker = Worker(queues, connection=conn, name=worker_name)
    worker.work(with_scheduler=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
