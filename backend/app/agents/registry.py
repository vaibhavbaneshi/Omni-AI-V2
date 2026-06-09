"""Agent type registry — maps agent_type to handler metadata."""

from __future__ import annotations

from typing import Any, Callable

AGENT_TYPES: dict[str, dict[str, Any]] = {
    "research": {
        "label": "Research Agent",
        "description": "Plans, searches, retrieves, synthesizes, and cites sources.",
        "default_schedule": "daily",
        "supports_schedule": True,
    },
    "document_monitor": {
        "label": "Document Monitor",
        "description": "Detects stale embeddings and re-indexing requirements.",
        "default_schedule": "daily",
        "supports_schedule": True,
    },
    "github_monitor": {
        "label": "GitHub Monitor",
        "description": "Watches connected GitHub repositories for changes.",
        "default_schedule": "daily",
        "supports_schedule": True,
    },
    "custom": {
        "label": "Custom Agent",
        "description": "User-configured agent from marketplace template.",
        "default_schedule": "manual",
        "supports_schedule": True,
    },
}


def get_agent_handler(agent_type: str) -> Callable[..., dict[str, Any]]:
    from app.agents.handlers.document_monitor import run_document_monitor
    from app.agents.handlers.github_monitor import run_github_monitor
    from app.agents.handlers.research import run_scheduled_research
    from app.agents.handlers.custom import run_custom_agent

    handlers = {
        "research": run_scheduled_research,
        "document_monitor": run_document_monitor,
        "github_monitor": run_github_monitor,
        "custom": run_custom_agent,
    }
    if agent_type not in handlers:
        raise ValueError(f"Unknown agent type: {agent_type}")
    return handlers[agent_type]


def list_agent_types() -> list[dict[str, Any]]:
    return [{"id": key, **value} for key, value in AGENT_TYPES.items()]
