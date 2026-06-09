"""Analytics API — user-scoped and admin platform metrics."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.admin_access import user_has_admin_access
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.analytics_service import get_platform_overview, get_user_overview
from app.services.redis_cache_service import cache_metrics
from sqlalchemy.orm import Session

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
def analytics_overview(
    days: int = Query(default=30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return analytics for the authenticated user."""
    return get_user_overview(db, user_id=current_user.id, days=days)


@router.get("/platform")
def analytics_platform(
    days: int = Query(default=30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Platform-wide metrics — admin only in production."""
    if not user_has_admin_access(current_user):
        raise HTTPException(status_code=403, detail="Platform analytics require admin access.")
    return get_platform_overview(db, days=days)


@router.get("/users")
def analytics_users(
    days: int = Query(default=30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user_has_admin_access(current_user):
        raise HTTPException(status_code=403, detail="User analytics require admin access.")

    overview = get_platform_overview(db, days=days)
    return {"period_days": days, "users": overview["users"]}


@router.get("/rag")
def analytics_rag(
    days: int = Query(default=30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user_has_admin_access(current_user):
        raise HTTPException(status_code=403, detail="RAG analytics require admin access.")

    overview = get_platform_overview(db, days=days)
    return {"period_days": days, "rag": overview["rag"], "ai": {"avg_latency_ms": overview["ai"]["avg_latency_ms"]}}


@router.get("/cache")
def analytics_cache_metrics(
    current_user: User = Depends(get_current_user),
):
    if not user_has_admin_access(current_user):
        raise HTTPException(status_code=403, detail="Cache metrics require admin access.")
    return cache_metrics()


@router.get("/agents")
def analytics_agent_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.autonomous_agent import AgentExecution, AutonomousAgent

    agents = db.query(AutonomousAgent).filter(AutonomousAgent.user_id == current_user.id).count()
    executions = (
        db.query(AgentExecution)
        .filter(AgentExecution.user_id == current_user.id)
        .order_by(AgentExecution.started_at.desc())
        .limit(100)
        .all()
    )
    complete = sum(1 for row in executions if row.status == "complete")
    failed = sum(1 for row in executions if row.status == "failed")
    tokens = sum(row.tokens_used or 0 for row in executions)
    latency = [row.latency_ms for row in executions if row.latency_ms]
    avg_latency = round(sum(latency) / len(latency), 2) if latency else 0
    return {
        "agents_total": agents,
        "runs_total": len(executions),
        "runs_complete": complete,
        "runs_failed": failed,
        "tokens_total": tokens,
        "avg_latency_ms": avg_latency,
        "recent": [
            {
                "id": row.id,
                "agent_id": row.agent_id,
                "status": row.status,
                "latency_ms": row.latency_ms,
                "started_at": row.started_at.isoformat() if row.started_at else None,
            }
            for row in executions[:20]
        ],
    }
