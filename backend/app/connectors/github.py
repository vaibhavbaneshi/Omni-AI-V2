"""GitHub connector adapter — wraps Phase L implementation."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.connectors.base import BaseConnector
from app.core.credential_crypto import encrypt_credentials
from app.models.connector_hub import ConnectorConnection
from app.models.user import User
from app.services import github_connector_service as gh


class GitHubConnector(BaseConnector):
    connector_type = "github"

    def connect(
        self,
        db: Session,
        *,
        user_id: int,
        credentials: dict[str, Any],
        display_name: str | None = None,
    ) -> ConnectorConnection:
        access_token = credentials.get("access_token")
        github_login = credentials.get("github_login")
        github_user_id = credentials.get("github_user_id")
        if not access_token:
            raise ValueError("GitHub access_token is required.")
        gh.save_connection(
            db,
            user_id=user_id,
            github_user_id=str(github_user_id or "0"),
            github_login=github_login or "github-user",
            access_token=access_token,
        )
        row = (
            db.query(ConnectorConnection)
            .filter(ConnectorConnection.user_id == user_id, ConnectorConnection.connector_type == "github")
            .first()
        )
        if row is None:
            row = ConnectorConnection(
                user_id=user_id,
                connector_type="github",
                display_name=display_name or github_login,
                credentials_encrypted=encrypt_credentials(credentials),
                connection_metadata={"github_login": github_login},
            )
            db.add(row)
        else:
            row.display_name = display_name or github_login
            row.credentials_encrypted = encrypt_credentials(credentials)
            row.connection_metadata = {"github_login": github_login}
            row.status = "connected"
        db.commit()
        db.refresh(row)
        return row

    def sync(self, db: Session, *, connection: ConnectorConnection, workspace_id: str = "default") -> dict[str, Any]:
        user = db.query(User).filter(User.id == connection.user_id).first()
        if not user:
            raise ValueError("User not found.")
        repo = (connection.connection_metadata or {}).get("repo_full_name")
        if not repo:
            repos = gh.list_repositories(db, user_id=user.id)
            if not repos:
                return {"files_indexed": 0, "document_count": 0, "message": "No repositories configured."}
            repo = repos[0]["full_name"]
        result = gh.sync_repository(db, user=user, repo_full_name=repo, workspace_id=workspace_id)
        connection.document_count = int(result.get("files_indexed") or 0)
        db.commit()
        return {
            "files_synced": result.get("files_indexed", 0),
            "files_indexed": result.get("files_indexed", 0),
            "document_count": connection.document_count,
            "status": result.get("status"),
        }
