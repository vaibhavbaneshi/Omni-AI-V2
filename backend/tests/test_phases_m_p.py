"""Tests for Phases M-P — agents, connectors, marketplace, research pipeline."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.agents.lifecycle import create_agent, pause_agent, resume_agent, serialize_agent
from app.agents.memory import add_memory_entry, list_memory_entries
from app.agents.registry import list_agent_types
from app.core.credential_crypto import decrypt_credentials, encrypt_credentials
from app.marketplace.catalog import install_template, list_templates, seed_marketplace_templates
from app.research.export import export_report_markdown
from app.research.planner import plan_research
from tests.factories import UserFactory


def test_credential_crypto_roundtrip():
    payload = {"access_token": "secret-token", "email": "user@example.com"}
    encrypted = encrypt_credentials(payload)
    assert decrypt_credentials(encrypted) == payload


def test_agent_types_registry():
    types = list_agent_types()
    assert any(item["id"] == "research" for item in types)
    assert any(item["id"] == "document_monitor" for item in types)


def test_create_pause_resume_agent(db_session):
    user = UserFactory()
    agent = create_agent(
        db_session,
        user_id=user.id,
        name="Daily Research",
        agent_type="document_monitor",
        schedule_kind="daily",
        config={"stale_days": 7},
    )
    assert agent.id is not None
    assert agent.next_run_at is not None

    paused = pause_agent(db_session, user_id=user.id, agent_id=agent.id)
    assert paused.status == "paused"

    resumed = resume_agent(db_session, user_id=user.id, agent_id=agent.id)
    assert resumed.status == "active"


def test_agent_memory_entries(db_session):
    user = UserFactory()
    agent = create_agent(
        db_session,
        user_id=user.id,
        name="Monitor",
        agent_type="document_monitor",
    )
    add_memory_entry(db_session, agent_id=agent.id, memory_type="goal", content="Track stale docs")
    rows = list_memory_entries(db_session, agent_id=agent.id)
    assert len(rows) == 1
    assert rows[0].memory_type == "goal"


@patch("app.services.llm_invoke.invoke_generate")
def test_research_planner_fallback(mock_invoke):
    mock_invoke.return_value = '{"goal":"Test","sub_problems":["a"],"search_queries":["a"]}'
    plan = plan_research("What is RAG?")
    assert plan["goal"]
    assert plan["search_queries"]


def test_export_report_markdown():
    md = export_report_markdown(
        {
            "title": "Report",
            "executive_summary": "Summary text",
            "key_findings": ["Finding 1"],
            "confidence_score": 0.82,
        },
        query="Test query",
    )
    assert "# Report" in md
    assert "Finding 1" in md
    assert "0.82" in md


def test_marketplace_seed_and_install(db_session):
    user = UserFactory()
    created = seed_marketplace_templates(db_session)
    assert created >= 1
    templates = list_templates(db_session)
    assert any(row.slug == "research-agent" for row in templates)
    result = install_template(db_session, user_id=user.id, slug="document-monitor-agent")
    assert result["agent"]["agent_type"] == "document_monitor"


@patch("app.connectors.notion.NotionConnector._search_pages", return_value=[])
def test_notion_connector_connect(mock_search, db_session):
    from app.connectors.notion import NotionConnector

    user = UserFactory()
    connector = NotionConnector()
    row = connector.connect(
        db_session,
        user_id=user.id,
        credentials={"api_token": "secret-notion-token"},
        display_name="My Notion",
    )
    assert row.connector_type == "notion"
    assert row.status == "connected"


def test_workspace_agents_api(auth_client, db_session):
    response = auth_client.post(
        "/agents/workspace",
        headers=auth_client.auth_headers,
        json={
            "name": "Test Monitor",
            "agent_type": "document_monitor",
            "schedule_kind": "manual",
            "config": {"stale_days": 10},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Test Monitor"


def test_marketplace_api(auth_client, db_session):
    seed_marketplace_templates(db_session)
    response = auth_client.get("/marketplace/templates", headers=auth_client.auth_headers)
    assert response.status_code == 200
    assert response.json()["templates"]


def test_connector_hub_status_api(auth_client):
    response = auth_client.get("/connectors/hub/status", headers=auth_client.auth_headers)
    assert response.status_code == 200
    assert response.json()["connectors"]
