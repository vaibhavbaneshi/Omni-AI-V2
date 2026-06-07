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
from app.services.ingestion_queue import INGEST_DLQ_NAME, INGEST_QUEUE_NAME

setup_logging()
logger = logging.getLogger("omniai.worker")


def main() -> int:
    from rq import Worker

    from app.core.app_settings import get_settings
    from app.core.redis_client import get_redis_connection
    from rq import Queue

    settings = get_settings()
    settings.validate_for_runtime()

    logger.info(
        "Starting ingestion worker queues=%s,%s embedding_provider=%s redis=%s pid=%s",
        INGEST_QUEUE_NAME,
        INGEST_DLQ_NAME,
        settings.EMBEDDING_PROVIDER,
        settings.redis_url.split("@")[-1] if settings.redis_url else "unset",
        os.getpid(),
    )

    conn = get_redis_connection()
    queues = [
        Queue(INGEST_QUEUE_NAME, connection=conn),
        Queue(INGEST_DLQ_NAME, connection=conn),
    ]
    worker = Worker(queues, connection=conn, name="omniai-ingest-worker")
    worker.work(with_scheduler=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
