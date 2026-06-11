"""RQ job entrypoint for autonomous agent execution."""

from __future__ import annotations

import logging
from datetime import timedelta

from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

AGENT_POLL_JOB_PATH = "app.jobs.agent_jobs.poll_due_agents_job"
AGENT_POLL_INTERVAL_SECONDS = 60
AGENT_POLL_LOCK_KEY = "omniai:agent_poll_scheduled"


def run_agent_job(agent_id: int) -> dict:
    from app.agents.executor import execute_agent

    db = SessionLocal()
    try:
        execution = execute_agent(db, agent_id=agent_id, trigger="scheduled")
        return {"execution_id": execution.id, "status": execution.status}
    finally:
        db.close()


def poll_due_agents() -> int:
    """Enqueue or run agents whose next_run_at is due."""
    from datetime import datetime

    from app.agents.scheduler import agents_due_for_run
    from app.services.agent_scheduler_service import enqueue_agent_run_now

    db = SessionLocal()
    count = 0
    try:
        for agent in agents_due_for_run(db, now=datetime.utcnow()):
            try:
                job_id = enqueue_agent_run_now(agent.id)
                if job_id:
                    count += 1
                    continue
                from app.agents.executor import execute_agent

                execute_agent(db, agent_id=agent.id, trigger="scheduled")
                count += 1
            except Exception:
                logger.exception("Scheduled agent run failed agent_id=%s", agent.id)
    finally:
        db.close()
    return count


def poll_due_agents_job() -> int:
    """RQ entrypoint — poll due agents and reschedule the next poll."""
    count = poll_due_agents()
    schedule_next_agent_poll()
    return count


def schedule_next_agent_poll() -> bool:
    """Schedule poll_due_agents to run again in 60 seconds. Returns False if Redis unavailable."""
    import redis
    from rq import Queue

    from app.core.app_settings import get_settings
    from app.core.redis_client import get_redis_connection, reset_redis_connection

    settings = get_settings()
    if not settings.redis_url:
        logger.debug("Redis not configured — autonomous agent scheduling skipped")
        return False

    try:
        conn = get_redis_connection()
        conn.ping()
        if not conn.set(AGENT_POLL_LOCK_KEY, "1", nx=True, ex=AGENT_POLL_INTERVAL_SECONDS - 5):
            return True

        queue = Queue("agents", connection=conn)
        queue.enqueue_in(
            timedelta(seconds=AGENT_POLL_INTERVAL_SECONDS),
            AGENT_POLL_JOB_PATH,
            job_timeout=300,
        )
        return True
    except (redis.ConnectionError, redis.TimeoutError, OSError) as exc:
        reset_redis_connection()
        logger.warning(
            "Autonomous agent poll scheduling skipped — Redis unavailable (%s). "
            "Start Redis locally (docker compose up redis -d) or set REDIS_HOST= to disable.",
            exc,
        )
        return False
    except Exception:
        reset_redis_connection()
        logger.exception("Autonomous agent poll scheduling failed unexpectedly")
        return False


def ensure_agent_poll_scheduled() -> None:
    """Start the recurring agent poll loop if not already scheduled."""
    schedule_next_agent_poll()
