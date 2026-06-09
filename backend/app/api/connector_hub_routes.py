"""Enterprise connector hub API — Phase N."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.connectors.registry import list_connector_types
from app.connectors.sync_engine import (
    disconnect_connector,
    get_connection_status,
    list_connections,
    list_sync_history,
    save_connection,
    serialize_connection,
    sync_connector,
)
from app.core.app_settings import get_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/connectors/hub", tags=["connectors", "hub"])


class ConnectorConnectRequest(BaseModel):
    connector_type: str
    credentials: dict = Field(default_factory=dict)
    display_name: str | None = None


class ConnectorSyncRequest(BaseModel):
    workspace_id: str = "default"


def _require_hub() -> None:
    if not get_settings().ENABLE_CONNECTOR_HUB:
        raise HTTPException(status_code=403, detail="Connector hub is disabled.")


@router.get("/types")
def connector_types(current_user: User = Depends(get_current_user)):
    _require_hub()
    return {"connectors": list_connector_types()}


@router.get("/status")
def connectors_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_hub()
    return {"connectors": get_connection_status(db, user_id=current_user.id)}


@router.post("/connect")
def connect_source(
    body: ConnectorConnectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_hub()
    try:
        row = save_connection(
            db,
            user_id=current_user.id,
            connector_type=body.connector_type,
            credentials=body.credentials,
            display_name=body.display_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_connection(row)


@router.post("/{connector_type}/sync")
def sync_source(
    connector_type: str,
    body: ConnectorSyncRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_hub()
    try:
        return sync_connector(db, user_id=current_user.id, connector_type=connector_type, workspace_id=body.workspace_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{connector_type}")
def disconnect_source(connector_type: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_hub()
    if not disconnect_connector(db, user_id=current_user.id, connector_type=connector_type):
        raise HTTPException(status_code=404, detail="Connector not connected.")
    return {"disconnected": True}


@router.get("/history")
def sync_history(
    connector_type: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_hub()
    rows = list_sync_history(db, user_id=current_user.id, connector_type=connector_type)
    return {
        "history": [
            {
                "id": row.id,
                "connection_id": row.connection_id,
                "status": row.status,
                "files_synced": row.files_synced,
                "error_message": row.error_message,
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "finished_at": row.finished_at.isoformat() if row.finished_at else None,
            }
            for row in rows
        ]
    }


@router.get("/connections")
def list_user_connections(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_hub()
    return {"connections": [serialize_connection(row) for row in list_connections(db, user_id=current_user.id)]}
