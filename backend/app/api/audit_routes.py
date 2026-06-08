"""Audit center and workspace connector APIs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.rbac import get_user_role, require_admin_or_manager
from app.db.session import get_db
from app.models.rbac import VALID_ROLES, UserRole
from app.models.user import User
from app.services.audit_service import get_audit_overview
from app.services.workspace_connector_service import get_connector, list_connectors, sync_connector

audit_router = APIRouter(prefix="/audit", tags=["audit"])
connector_router = APIRouter(prefix="/connectors", tags=["connectors"])


@audit_router.get("/overview")
def audit_overview(
    days: int = Query(default=30, ge=1, le=90),
    current_user: User = Depends(require_admin_or_manager()),
    db: Session = Depends(get_db),
):
    return get_audit_overview(db, days=days)


@audit_router.get("/role")
def read_my_role(
    current_user: User = Depends(require_admin_or_manager()),
    db: Session = Depends(get_db),
):
    return {"user_id": current_user.id, "role": get_user_role(db, current_user)}


@audit_router.put("/role/{user_id}")
def assign_role(
    user_id: int,
    role: str = Query(...),
    current_user: User = Depends(require_admin_or_manager()),
    db: Session = Depends(get_db),
):
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Choose from: {sorted(VALID_ROLES)}")

    record = db.query(UserRole).filter(UserRole.user_id == user_id).first()
    if record is None:
        record = UserRole(user_id=user_id, role=role)
        db.add(record)
    else:
        record.role = role
    db.commit()
    db.refresh(record)
    return {"user_id": user_id, "role": record.role}


@connector_router.get("")
def connectors_list(current_user: User = Depends(require_admin_or_manager())):
    return {"connectors": list_connectors()}


@connector_router.get("/{connector_id}")
def connectors_detail(
    connector_id: str,
    current_user: User = Depends(require_admin_or_manager()),
):
    connector = get_connector(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found.")
    return connector


@connector_router.post("/{connector_id}/sync")
def connectors_sync(
    connector_id: str,
    current_user: User = Depends(require_admin_or_manager()),
):
    try:
        return sync_connector(connector_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
