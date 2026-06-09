"""Google Drive connector — indexes text documents via Drive API."""

from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.connectors.base import BaseConnector
from app.connectors.indexing import ensure_connector_collection, index_connector_text
from app.connectors.sync_engine import get_decrypted_credentials
from app.core.credential_crypto import encrypt_credentials
from app.models.connector_hub import ConnectorConnection
from app.models.user import User

DRIVE_API = "https://www.googleapis.com/drive/v3"
EXPORT_MIMES = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
}


class GoogleDriveConnector(BaseConnector):
    connector_type = "google_drive"

    def connect(
        self,
        db: Session,
        *,
        user_id: int,
        credentials: dict[str, Any],
        display_name: str | None = None,
    ) -> ConnectorConnection:
        access_token = credentials.get("access_token")
        if not access_token:
            raise ValueError("Google Drive access_token is required.")
        self._list_files(access_token)
        encrypted = encrypt_credentials(credentials)
        row = (
            db.query(ConnectorConnection)
            .filter(ConnectorConnection.user_id == user_id, ConnectorConnection.connector_type == "google_drive")
            .first()
        )
        if row is None:
            row = ConnectorConnection(
                user_id=user_id,
                connector_type="google_drive",
                display_name=display_name or "Google Drive",
                credentials_encrypted=encrypted,
                status="connected",
            )
            db.add(row)
        else:
            row.credentials_encrypted = encrypted
            row.status = "connected"
        db.commit()
        db.refresh(row)
        return row

    def sync(self, db: Session, *, connection: ConnectorConnection, workspace_id: str = "default") -> dict[str, Any]:
        creds = get_decrypted_credentials(connection)
        token = creds["access_token"]
        user = db.query(User).filter(User.id == connection.user_id).first()
        if not user:
            raise ValueError("User not found.")
        files = self._list_files(token)
        collection = ensure_connector_collection(db, user_id=user.id, workspace_id=workspace_id, name="Google Drive")
        synced = 0
        for item in files:
            file_id = item.get("id")
            name = item.get("name") or file_id
            mime = item.get("mimeType") or ""
            text = self._download_text(token, file_id, mime)
            if not text.strip():
                continue
            filename = f"gdrive__{file_id}__{name.replace('/', '_')[:80]}.txt"
            index_connector_text(
                db,
                user=user,
                collection_id=collection.id,
                workspace_id=workspace_id,
                source_key=file_id,
                filename=filename,
                text=text,
            )
            synced += 1
        connection.document_count = synced
        db.commit()
        return {"files_synced": synced, "document_count": synced}

    def _headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def _list_files(self, token: str) -> list[dict[str, Any]]:
        response = httpx.get(
            f"{DRIVE_API}/files",
            headers=self._headers(token),
            params={
                "pageSize": 50,
                "fields": "files(id,name,mimeType,modifiedTime)",
                "q": "trashed=false",
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get("files", [])

    def _download_text(self, token: str, file_id: str, mime: str) -> str:
        if mime in EXPORT_MIMES:
            export_mime = EXPORT_MIMES[mime]
            response = httpx.get(
                f"{DRIVE_API}/files/{file_id}/export",
                headers=self._headers(token),
                params={"mimeType": export_mime},
                timeout=60,
            )
        elif mime.startswith("text/") or mime in {"application/json", "application/pdf"}:
            response = httpx.get(
                f"{DRIVE_API}/files/{file_id}",
                headers=self._headers(token),
                params={"alt": "media"},
                timeout=60,
            )
        else:
            return ""
        response.raise_for_status()
        return response.text[:512_000]
