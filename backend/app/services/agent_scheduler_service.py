"""RQ scheduling for autonomous agent runs."""

from __future__ import annotations

import logging
from datetime import datetime

from app.core.app_settings import get_settings

logger = logging.getLogger(__name__)

AGENT_JOB_PATH = "app.jobs.agent_jobs.run_agent_job"
AGENT_QUEUE_NAME = "agents"


def _get_agent_queue():
    settings = get_settings()
    if not settings.redis_url:
        return None
    from rq import Queue

    from app.core.redis_client import get_redis_connection

    return Queue(AGENT_QUEUE_NAME, connection=get_redis_connection())


def enqueue_agent_run(agent_id: int, *, run_at: datetime | None = None) -> str | None:
    queue = _get_agent_queue()
    if queue is None:
        logger.debug("Agent queue unavailable — inline execution only agent_id=%s", agent_id)
        return None
    job = queue.enqueue_at(run_at, AGENT_JOB_PATH, agent_id, job_timeout=1800)
    return job.id


def enqueue_agent_run_now(agent_id: int) -> str | None:
    queue = _get_agent_queue()
    if queue is None:
        return None
    job = queue.enqueue(AGENT_JOB_PATH, agent_id, job_timeout=1800)
    return job.id
