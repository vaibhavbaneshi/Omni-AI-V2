"""In-app notifications and email abstraction."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.autonomous_agent import Notification
from app.services.email_service import send_email_notification

logger = logging.getLogger(__name__)


def notify_user(
    db: Session,
    *,
    user_id: int,
    title: str,
    body: str | None = None,
    category: str = "system",
    link: str | None = None,
    send_email: bool = False,
) -> Notification:
    row = Notification(
        user_id=user_id,
        title=title,
        body=body,
        category=category,
        link=link,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    if send_email:
        try:
            from app.models.user import User

            user = db.query(User).filter(User.id == user_id).first()
            if user and user.email:
                send_email_notification(
                    to_email=user.email,
                    subject=title,
                    body=body or title,
                    link=link,
                )
        except Exception:
            logger.exception("Email notification failed user_id=%s", user_id)

    return row


def list_notifications(
    db: Session,
    *,
    user_id: int,
    unread_only: bool = False,
    limit: int = 50,
) -> list[Notification]:
    query = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        query = query.filter(Notification.read.is_(False))
    return query.order_by(Notification.created_at.desc()).limit(limit).all()


def mark_notification_read(db: Session, *, user_id: int, notification_id: int) -> bool:
    row = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )
    if not row:
        return False
    row.read = True
    db.commit()
    return True


def mark_all_read(db: Session, *, user_id: int) -> int:
    rows = db.query(Notification).filter(Notification.user_id == user_id, Notification.read.is_(False)).all()
    for row in rows:
        row.read = True
    db.commit()
    return len(rows)


def serialize_notification(row: Notification) -> dict[str, Any]:
    return {
        "id": row.id,
        "title": row.title,
        "body": row.body,
        "category": row.category,
        "link": row.link,
        "read": row.read,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
