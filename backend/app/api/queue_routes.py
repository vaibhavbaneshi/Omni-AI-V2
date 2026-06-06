"""Admin API for ingestion queue monitoring and recovery."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.admin_access import user_has_admin_access
from app.core.security import get_current_user
from app.models.user import User
from app.services.ingestion_queue import (
    get_ingestion_queue_metrics,
    ingest_queue_enabled,
    list_recent_dlq_jobs,
    requeue_failed_job,
)

router = APIRouter(prefix="/admin/ingestion-queue", tags=["ingestion-queue"])


def require_queue_admin(current_user: User = Depends(get_current_user)) -> User:
    if not user_has_admin_access(current_user):
        raise HTTPException(status_code=403, detail="Ingestion queue admin access required.")
    return current_user


@router.get("/metrics")
def ingestion_queue_metrics(_: User = Depends(require_queue_admin)):
    if not ingest_queue_enabled():
        return {
            "enabled": False,
            "message": "RQ ingestion queue is disabled (INGEST_QUEUE_ENABLED=false or sync mode).",
        }
    return {"enabled": True, **get_ingestion_queue_metrics()}


@router.get("/dlq")
def ingestion_dlq_jobs(
    limit: int = 20,
    _: User = Depends(require_queue_admin),
):
    if not ingest_queue_enabled():
        raise HTTPException(status_code=503, detail="Ingestion queue is not enabled.")
    return {"jobs": list_recent_dlq_jobs(limit=min(limit, 100))}


@router.post("/requeue/{job_id}")
def requeue_ingestion_job(
    job_id: str,
    _: User = Depends(require_queue_admin),
):
    if not ingest_queue_enabled():
        raise HTTPException(status_code=503, detail="Ingestion queue is not enabled.")
    try:
        new_job_id = requeue_failed_job(job_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Unable to requeue job: {exc}") from exc
    return {"message": "Job requeued", "new_job_id": new_job_id}
