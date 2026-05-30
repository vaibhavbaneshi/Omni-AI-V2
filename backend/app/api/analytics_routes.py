"""Analytics API — user-scoped and admin platform metrics."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.admin_access import user_has_admin_access
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.analytics_service import get_platform_overview, get_user_overview
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
