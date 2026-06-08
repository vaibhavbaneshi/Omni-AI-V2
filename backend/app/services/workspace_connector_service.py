"""Workspace connector registry — GitHub, Notion, Confluence, Slack stubs."""

from __future__ import annotations

from typing import Any

from app.core.app_settings import get_settings

CONNECTOR_DEFINITIONS = (
    {
        "id": "github",
        "name": "GitHub",
        "description": "Sync repositories, issues, and pull requests into workspace context.",
        "env_keys": ("GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET"),
    },
    {
        "id": "notion",
        "name": "Notion",
        "description": "Import Notion pages and databases for retrieval.",
        "env_keys": ("NOTION_API_KEY",),
    },
    {
        "id": "confluence",
        "name": "Confluence",
        "description": "Sync Confluence spaces and pages.",
        "env_keys": ("CONFLUENCE_BASE_URL", "CONFLUENCE_API_TOKEN"),
    },
    {
        "id": "slack",
        "name": "Slack",
        "description": "Index channel history and thread summaries.",
        "env_keys": ("SLACK_BOT_TOKEN",),
    },
)


def _connector_configured(definition: dict[str, Any]) -> bool:
    settings = get_settings()
    for key in definition["env_keys"]:
        if not getattr(settings, key, ""):
            return False
    return True


def list_connectors() -> list[dict[str, Any]]:
    return [
        {
            **definition,
            "status": "configured" if _connector_configured(definition) else "not_configured",
            "connected": False,
        }
        for definition in CONNECTOR_DEFINITIONS
    ]


def get_connector(connector_id: str) -> dict[str, Any] | None:
    for definition in CONNECTOR_DEFINITIONS:
        if definition["id"] == connector_id:
            return {
                **definition,
                "status": "configured" if _connector_configured(definition) else "not_configured",
                "connected": False,
            }
    return None


def sync_connector(connector_id: str) -> dict[str, Any]:
    connector = get_connector(connector_id)
    if not connector:
        raise LookupError(f"Unknown connector: {connector_id}")
    if connector["status"] != "configured":
        raise ValueError(f"Connector {connector_id} is not configured in environment.")
    return {
        "connector_id": connector_id,
        "status": "queued",
        "message": f"{connector['name']} sync queued (stub — implement OAuth/webhook flow).",
    }
