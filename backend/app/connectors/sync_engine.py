"""Connector sync engine — connection CRUD and sync orchestration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.connectors.registry import get_connector_class, list_connector_types
from app.core.credential_crypto import decrypt_credentials, encrypt_credentials
from app.models.connector_hub import ConnectorConnection, ConnectorSyncRun


def save_connection(
    db: Session,
    *,
    user_id: int,
    connector_type: str,
    credentials: dict[str, Any],
    display_name: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ConnectorConnection:
    connector_cls = get_connector_class(connector_type)
    connector = connector_cls()
    return connector.connect(db, user_id=user_id, credentials=credentials, display_name=display_name)


def list_connections(db: Session, *, user_id: int) -> list[ConnectorConnection]:
    return (
        db.query(ConnectorConnection)
        .filter(ConnectorConnection.user_id == user_id)
        .order_by(ConnectorConnection.connector_type.asc())
        .all()
    )


def get_connection(db: Session, *, user_id: int, connector_type: str) -> ConnectorConnection | None:
    return (
        db.query(ConnectorConnection)
        .filter(
            ConnectorConnection.user_id == user_id,
            ConnectorConnection.connector_type == connector_type,
        )
        .first()
    )


def disconnect_connector(db: Session, *, user_id: int, connector_type: str) -> bool:
    connection = get_connection(db, user_id=user_id, connector_type=connector_type)
    if not connection:
        return False
    connector_cls = get_connector_class(connector_type)
    connector_cls().disconnect(db, connection=connection)
    return True


def sync_connector(
    db: Session,
    *,
    user_id: int,
    connector_type: str,
    workspace_id: str = "default",
) -> dict[str, Any]:
    connection = get_connection(db, user_id=user_id, connector_type=connector_type)
    if not connection:
        raise ValueError(f"{connector_type} is not connected.")

    run = ConnectorSyncRun(
        connection_id=connection.id,
        user_id=user_id,
        status="running",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        connector = get_connector_class(connector_type)()
        result = connector.sync(db, connection=connection, workspace_id=workspace_id)
        run.status = "complete"
        run.files_synced = int(result.get("files_synced") or result.get("files_indexed") or 0)
        run.sync_metadata = result
        connection.last_sync_at = datetime.utcnow()
        connection.document_count = int(result.get("document_count") or connection.document_count or 0)
        db.commit()
        return {"sync_run_id": run.id, **result}
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)[:2000]
        db.commit()
        raise


def list_sync_history(db: Session, *, user_id: int, connector_type: str | None = None, limit: int = 20) -> list[ConnectorSyncRun]:
    query = db.query(ConnectorSyncRun).filter(ConnectorSyncRun.user_id == user_id)
    if connector_type:
        connections = (
            db.query(ConnectorConnection)
            .filter(
                ConnectorConnection.user_id == user_id,
                ConnectorConnection.connector_type == connector_type,
            )
            .all()
        )
        connection_ids = [row.id for row in connections]
        query = query.filter(ConnectorSyncRun.connection_id.in_(connection_ids))
    return query.order_by(ConnectorSyncRun.started_at.desc()).limit(limit).all()


def get_connection_status(db: Session, *, user_id: int) -> list[dict[str, Any]]:
    types = list_connector_types()
    connections = {row.connector_type: row for row in list_connections(db, user_id=user_id)}
    payload = []
    for item in types:
        conn = connections.get(item["id"])
        payload.append(
            {
                **item,
                "connected": conn is not None,
                "display_name": conn.display_name if conn else None,
                "last_sync_at": conn.last_sync_at.isoformat() if conn and conn.last_sync_at else None,
                "document_count": conn.document_count if conn else 0,
                "status": conn.status if conn else "disconnected",
            }
        )
    return payload


def serialize_connection(row: ConnectorConnection) -> dict[str, Any]:
    return {
        "connector_type": row.connector_type,
        "display_name": row.display_name,
        "status": row.status,
        "last_sync_at": row.last_sync_at.isoformat() if row.last_sync_at else None,
        "document_count": row.document_count,
        "metadata": row.connection_metadata,
    }


def get_decrypted_credentials(connection: ConnectorConnection) -> dict[str, Any]:
    return decrypt_credentials(connection.credentials_encrypted)
