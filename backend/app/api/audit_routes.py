"""Audit center and workspace connector APIs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.core.rbac import ROLE_ADMIN, get_user_role, require_admin_or_manager, user_has_min_role
from app.db.session import get_db
from app.models.rbac import VALID_ROLES, UserRole
from app.models.user import User
from app.services.audit_service import (
    export_audit_events_csv,
    get_audit_overview,
    list_audit_events,
    list_users_with_roles,
)
from app.services.security_audit_service import audit_log
from app.services.workspace_connector_service import get_connector, list_connectors, sync_connector

audit_router = APIRouter(prefix="/audit", tags=["audit"])
connector_router = APIRouter(prefix="/admin/connectors", tags=["connectors", "admin"])


def require_admin():
    return require_admin_or_manager()


@audit_router.get("/overview")
def audit_overview(
    days: int = Query(default=30, ge=1, le=90),
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
):
    return get_audit_overview(db, days=days)


@audit_router.get("/events")
def audit_events(
    days: int = Query(default=30, ge=1, le=90),
    action_prefix: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
):
    return list_audit_events(
        db,
        days=days,
        action_prefix=action_prefix,
        limit=limit,
        offset=offset,
    )


@audit_router.get("/export")
def audit_export(
    days: int = Query(default=30, ge=1, le=90),
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
):
    csv_data = export_audit_events_csv(db, days=days)
    return PlainTextResponse(csv_data, media_type="text/csv")


@audit_router.get("/users")
def audit_users(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
):
    return list_users_with_roles(db, limit=limit, offset=offset)


@audit_router.get("/role")
def read_my_role(
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
):
    return {"user_id": current_user.id, "role": get_user_role(db, current_user)}


@audit_router.put("/role/{user_id}")
def assign_role(
    user_id: int,
    role: str = Query(...),
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
):
    if not user_has_min_role(db, current_user, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Only admins may assign roles.")
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Choose from: {sorted(VALID_ROLES)}")

    record = db.query(UserRole).filter(UserRole.user_id == user_id).first()
    previous = record.role if record else None
    if record is None:
        record = UserRole(user_id=user_id, role=role)
        db.add(record)
    else:
        record.role = role
    db.commit()
    db.refresh(record)
    audit_log(
        db,
        action="rbac.role.changed",
        user_id=current_user.id,
        detail={"target_user_id": user_id, "previous_role": previous, "new_role": role},
    )
    return {"user_id": user_id, "role": record.role}


@connector_router.get("")
def connectors_list(current_user: User = Depends(require_admin())):
    return {"connectors": list_connectors()}


@connector_router.get("/{connector_id}")
def connectors_detail(
    connector_id: str,
    current_user: User = Depends(require_admin()),
):
    connector = get_connector(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found.")
    return connector


@connector_router.post("/{connector_id}/sync")
def connectors_sync(
    connector_id: str,
    current_user: User = Depends(require_admin()),
):
    try:
        return sync_connector(connector_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
