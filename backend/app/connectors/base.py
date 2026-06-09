"""Base connector interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.orm import Session

from app.models.connector_hub import ConnectorConnection


class BaseConnector(ABC):
    connector_type: str = ""

    @abstractmethod
    def connect(self, db: Session, *, user_id: int, credentials: dict[str, Any], display_name: str | None = None) -> ConnectorConnection:
        ...

    @abstractmethod
    def sync(self, db: Session, *, connection: ConnectorConnection, workspace_id: str = "default") -> dict[str, Any]:
        ...

    def disconnect(self, db: Session, *, connection: ConnectorConnection) -> None:
        db.delete(connection)
        db.commit()
