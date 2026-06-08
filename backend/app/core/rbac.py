"""RBAC helpers — role lookup and route guards."""

from __future__ import annotations

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.admin_access import user_has_admin_access
from app.core.app_settings import get_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.rbac import DEFAULT_ROLE, ROLE_ADMIN, ROLE_EDITOR, ROLE_MANAGER, ROLE_VIEWER, UserRole
from app.models.user import User

ROLE_RANK = {
    ROLE_VIEWER: 1,
    ROLE_EDITOR: 2,
    ROLE_MANAGER: 3,
    ROLE_ADMIN: 4,
}


def get_user_role(db: Session, user: User) -> str:
    record = db.query(UserRole).filter(UserRole.user_id == user.id).first()
    if record:
        return record.role
    if user_has_admin_access(user):
        return ROLE_ADMIN
    return DEFAULT_ROLE


def ensure_user_role(db: Session, user: User, *, role: str = DEFAULT_ROLE) -> UserRole:
    record = db.query(UserRole).filter(UserRole.user_id == user.id).first()
    if record:
        return record
    record = UserRole(user_id=user.id, role=role)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def user_has_min_role(db: Session, user: User, minimum_role: str) -> bool:
    settings = get_settings()
    if not settings.ENABLE_RBAC:
        return True
    if user_has_admin_access(user):
        return True
    current = get_user_role(db, user)
    return ROLE_RANK.get(current, 0) >= ROLE_RANK.get(minimum_role, 0)


def require_min_role(minimum_role: str):
    def dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        settings = get_settings()
        if not settings.ENABLE_RBAC:
            if user_has_admin_access(current_user):
                return current_user
            raise HTTPException(status_code=403, detail="Admin access required.")
        if not user_has_min_role(db, current_user, minimum_role):
            raise HTTPException(status_code=403, detail=f"Requires {minimum_role} role or higher.")
        return current_user

    return dependency


def require_admin_or_manager():
    return require_min_role(ROLE_MANAGER)
