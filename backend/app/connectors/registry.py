"""Connector type registry."""

from __future__ import annotations

from typing import Any, Type

from app.connectors.base import BaseConnector

CONNECTOR_TYPES: dict[str, dict[str, Any]] = {
    "github": {
        "label": "GitHub",
        "description": "Sync repositories into workspace collections.",
        "auth": "oauth",
    },
    "notion": {
        "label": "Notion",
        "description": "Import Notion pages and databases.",
        "auth": "token",
    },
    "confluence": {
        "label": "Confluence",
        "description": "Sync Confluence spaces and pages.",
        "auth": "token",
    },
    "google_drive": {
        "label": "Google Drive",
        "description": "Index documents from Google Drive.",
        "auth": "oauth",
    },
    "dropbox": {
        "label": "Dropbox",
        "description": "Sync files from Dropbox folders.",
        "auth": "oauth",
    },
}


def get_connector_class(connector_type: str) -> Type[BaseConnector]:
    from app.connectors.confluence import ConfluenceConnector
    from app.connectors.dropbox import DropboxConnector
    from app.connectors.github import GitHubConnector
    from app.connectors.google_drive import GoogleDriveConnector
    from app.connectors.notion import NotionConnector

    mapping = {
        "github": GitHubConnector,
        "notion": NotionConnector,
        "confluence": ConfluenceConnector,
        "google_drive": GoogleDriveConnector,
        "dropbox": DropboxConnector,
    }
    if connector_type not in mapping:
        raise ValueError(f"Unknown connector type: {connector_type}")
    return mapping[connector_type]


def list_connector_types() -> list[dict[str, Any]]:
    return [{"id": key, **value} for key, value in CONNECTOR_TYPES.items()]
