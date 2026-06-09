"""In-app notifications API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.notification_service import (
    list_notifications,
    mark_all_read,
    mark_notification_read,
    serialize_notification,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


class MarkReadRequest(BaseModel):
    read: bool = True


@router.get("")
def get_notifications(
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = list_notifications(db, user_id=current_user.id, unread_only=unread_only)
    return {"notifications": [serialize_notification(row) for row in rows]}


@router.post("/{notification_id}/read")
def read_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not mark_notification_read(db, user_id=current_user.id, notification_id=notification_id):
        raise HTTPException(status_code=404, detail="Notification not found.")
    return {"read": True}


@router.post("/read-all")
def read_all_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = mark_all_read(db, user_id=current_user.id)
    return {"marked_read": count}
