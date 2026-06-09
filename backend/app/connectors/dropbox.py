"""Dropbox connector — syncs text files from Dropbox."""

from __future__ import annotations

import json
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.connectors.base import BaseConnector
from app.connectors.indexing import ensure_connector_collection, index_connector_text
from app.connectors.sync_engine import get_decrypted_credentials
from app.core.credential_crypto import encrypt_credentials
from app.models.connector_hub import ConnectorConnection
from app.models.user import User

DROPBOX_API = "https://api.dropboxapi.com/2"
CONTENT_API = "https://content.dropboxapi.com/2"
TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".json", ".csv", ".html", ".htm", ".py", ".js", ".ts"}


class DropboxConnector(BaseConnector):
    connector_type = "dropbox"

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
            raise ValueError("Dropbox access_token is required.")
        httpx.post(
            f"{DROPBOX_API}/users/get_current_account",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        ).raise_for_status()
        encrypted = encrypt_credentials(credentials)
        row = (
            db.query(ConnectorConnection)
            .filter(ConnectorConnection.user_id == user_id, ConnectorConnection.connector_type == "dropbox")
            .first()
        )
        if row is None:
            row = ConnectorConnection(
                user_id=user_id,
                connector_type="dropbox",
                display_name=display_name or "Dropbox",
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
        entries = self._list_folder(token, "")
        collection = ensure_connector_collection(db, user_id=user.id, workspace_id=workspace_id, name="Dropbox")
        synced = 0
        for entry in entries:
            if entry.get(".tag") != "file":
                continue
            path = entry.get("path_display") or entry.get("name") or ""
            ext = path[path.rfind(".") :].lower() if "." in path else ""
            if ext not in TEXT_EXTENSIONS:
                continue
            text = self._download_file(token, path)
            if not text.strip():
                continue
            filename = f"dropbox__{path.strip('/').replace('/', '__')}"
            index_connector_text(
                db,
                user=user,
                collection_id=collection.id,
                workspace_id=workspace_id,
                source_key=path,
                filename=filename,
                text=text,
            )
            synced += 1
        connection.document_count = synced
        db.commit()
        return {"files_synced": synced, "document_count": synced}

    def _list_folder(self, token: str, path: str) -> list[dict[str, Any]]:
        response = httpx.post(
            f"{DROPBOX_API}/files/list_folder",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"path": path, "recursive": True, "limit": 100},
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get("entries", [])

    def _download_file(self, token: str, path: str) -> str:
        response = httpx.post(
            f"{CONTENT_API}/files/download",
            headers={
                "Authorization": f"Bearer {token}",
                "Dropbox-API-Arg": json.dumps({"path": path}),
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.text[:512_000]
