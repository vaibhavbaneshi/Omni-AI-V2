"""Confluence connector — syncs space pages via REST API."""

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


class ConfluenceConnector(BaseConnector):
    connector_type = "confluence"

    def connect(
        self,
        db: Session,
        *,
        user_id: int,
        credentials: dict[str, Any],
        display_name: str | None = None,
    ) -> ConnectorConnection:
        base_url = (credentials.get("base_url") or "").rstrip("/")
        email = credentials.get("email")
        api_token = credentials.get("api_token")
        if not base_url or not email or not api_token:
            raise ValueError("Confluence requires base_url, email, and api_token.")
        self._list_pages(base_url, email, api_token)
        encrypted = encrypt_credentials({"base_url": base_url, "email": email, "api_token": api_token})
        row = (
            db.query(ConnectorConnection)
            .filter(ConnectorConnection.user_id == user_id, ConnectorConnection.connector_type == "confluence")
            .first()
        )
        if row is None:
            row = ConnectorConnection(
                user_id=user_id,
                connector_type="confluence",
                display_name=display_name or "Confluence",
                credentials_encrypted=encrypted,
                status="connected",
                connection_metadata={"base_url": base_url},
            )
            db.add(row)
        else:
            row.credentials_encrypted = encrypted
            row.connection_metadata = {"base_url": base_url}
            row.status = "connected"
        db.commit()
        db.refresh(row)
        return row

    def sync(self, db: Session, *, connection: ConnectorConnection, workspace_id: str = "default") -> dict[str, Any]:
        creds = get_decrypted_credentials(connection)
        user = db.query(User).filter(User.id == connection.user_id).first()
        if not user:
            raise ValueError("User not found.")
        pages = self._list_pages(creds["base_url"], creds["email"], creds["api_token"])
        collection = ensure_connector_collection(db, user_id=user.id, workspace_id=workspace_id, name="Confluence")
        synced = 0
        for page in pages:
            page_id = page.get("id")
            title = page.get("title") or "Untitled"
            body = (((page.get("body") or {}).get("storage") or {}).get("value")) or ""
            if not body.strip():
                continue
            filename = f"confluence__{page_id}.html"
            index_connector_text(
                db,
                user=user,
                collection_id=collection.id,
                workspace_id=workspace_id,
                source_key=str(page_id),
                filename=filename,
                text=f"# {title}\n\n{body}",
            )
            synced += 1
        connection.document_count = synced
        db.commit()
        return {"files_synced": synced, "document_count": synced}

    def _list_pages(self, base_url: str, email: str, api_token: str) -> list[dict[str, Any]]:
        response = httpx.get(
            f"{base_url}/wiki/rest/api/content",
            auth=(email, api_token),
            params={"type": "page", "limit": 50, "expand": "body.storage"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get("results", [])
