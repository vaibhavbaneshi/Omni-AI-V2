"""Notion connector — indexes searchable pages via Notion API."""

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

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionConnector(BaseConnector):
    connector_type = "notion"

    def connect(
        self,
        db: Session,
        *,
        user_id: int,
        credentials: dict[str, Any],
        display_name: str | None = None,
    ) -> ConnectorConnection:
        token = credentials.get("api_token") or credentials.get("token")
        if not token:
            raise ValueError("Notion api_token is required.")
        self._search_pages(token, query="")
        row = (
            db.query(ConnectorConnection)
            .filter(ConnectorConnection.user_id == user_id, ConnectorConnection.connector_type == "notion")
            .first()
        )
        encrypted = encrypt_credentials({"api_token": token})
        if row is None:
            row = ConnectorConnection(
                user_id=user_id,
                connector_type="notion",
                display_name=display_name or "Notion",
                credentials_encrypted=encrypted,
                status="connected",
            )
            db.add(row)
        else:
            row.credentials_encrypted = encrypted
            row.display_name = display_name or row.display_name
            row.status = "connected"
        db.commit()
        db.refresh(row)
        return row

    def sync(self, db: Session, *, connection: ConnectorConnection, workspace_id: str = "default") -> dict[str, Any]:
        creds = get_decrypted_credentials(connection)
        token = creds.get("api_token") or creds.get("token")
        user = db.query(User).filter(User.id == connection.user_id).first()
        if not user:
            raise ValueError("User not found.")
        pages = self._search_pages(token, query="")
        collection = ensure_connector_collection(db, user_id=user.id, workspace_id=workspace_id, name="Notion")
        synced = 0
        for page in pages:
            page_id = page.get("id")
            title = self._page_title(page)
            text = self._fetch_page_text(token, page_id)
            if not text.strip():
                continue
            filename = f"notion__{page_id.replace('-', '')}.md"
            index_connector_text(
                db,
                user=user,
                collection_id=collection.id,
                workspace_id=workspace_id,
                source_key=page_id,
                filename=filename,
                text=f"# {title}\n\n{text}",
            )
            synced += 1
        connection.document_count = synced
        db.commit()
        return {"files_synced": synced, "document_count": synced}

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    def _search_pages(self, token: str, query: str) -> list[dict[str, Any]]:
        response = httpx.post(
            f"{NOTION_API}/search",
            headers=self._headers(token),
            json={"query": query, "page_size": 50},
            timeout=30,
        )
        response.raise_for_status()
        return [item for item in response.json().get("results", []) if item.get("object") == "page"]

    def _page_title(self, page: dict[str, Any]) -> str:
        props = page.get("properties") or {}
        for prop in props.values():
            if prop.get("type") == "title":
                parts = prop.get("title") or []
                return "".join(part.get("plain_text", "") for part in parts) or "Untitled"
        return "Untitled"

    def _fetch_page_text(self, token: str, page_id: str) -> str:
        response = httpx.get(
            f"{NOTION_API}/blocks/{page_id}/children",
            headers=self._headers(token),
            params={"page_size": 100},
            timeout=30,
        )
        response.raise_for_status()
        lines = []
        for block in response.json().get("results", []):
            block_type = block.get("type")
            data = block.get(block_type) or {}
            rich = data.get("rich_text") or []
            text = "".join(item.get("plain_text", "") for item in rich)
            if text:
                lines.append(text)
        return "\n\n".join(lines)
