"""Role-based access control models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

from app.db.database import Base

ROLE_ADMIN = "admin"
ROLE_MANAGER = "manager"
ROLE_EDITOR = "editor"
ROLE_VIEWER = "viewer"

DEFAULT_ROLE = ROLE_VIEWER
VALID_ROLES = {ROLE_ADMIN, ROLE_MANAGER, ROLE_EDITOR, ROLE_VIEWER}


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_roles_user_id"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(32), nullable=False, default=DEFAULT_ROLE)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
