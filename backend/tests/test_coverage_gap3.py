"""Additional coverage for connectors, research export, and scheduler."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.connectors.registry import get_connector_class, list_connector_types
from app.connectors.sync_engine import (
    disconnect_connector,
    get_connection_status,
    list_connections,
    save_connection,
    serialize_connection,
    sync_connector,
)
from app.models.connector_hub import ConnectorConnection
from app.research.export import export_report_markdown, export_report_pdf_bytes
from app.services.agent_scheduler_service import enqueue_agent_run, enqueue_agent_run_now
from app.services.email_service import send_email_notification
from tests.factories import UserFactory


SAMPLE_REPORT = {
    "title": "Coverage Report",
    "executive_summary": "Summary text.",
    "key_findings": ["Finding one"],
    "detailed_analysis": "Details here.",
    "evidence_summary": "Evidence.",
    "contradictions_noted": ["None"],
    "confidence_score": 0.91,
    "references": [{"label": "Source", "url": "https://example.com"}],
}


def test_list_connector_types():
    types = list_connector_types()
    assert any(item["id"] == "notion" for item in types)


def test_get_connector_class_unknown():
    with pytest.raises(ValueError, match="Unknown connector"):
        get_connector_class("invalid")


def test_export_report_markdown_includes_sections():
    markdown = export_report_markdown(SAMPLE_REPORT, query="Q")
    assert "# Coverage Report" in markdown
    assert "## Key Findings" in markdown
    assert "Finding one" in markdown
    assert "Confidence score" in markdown


def test_export_report_pdf_bytes_returns_pdf():
    pdf = export_report_pdf_bytes(SAMPLE_REPORT, query="Q")
    assert pdf.startswith(b"%PDF")


@patch("app.services.email_service.smtplib.SMTP")
@patch("app.services.email_service.get_settings")
def test_send_email_notification_smtp(mock_settings, mock_smtp):
    settings = MagicMock()
    settings.SMTP_HOST = "smtp.test"
    settings.SMTP_PORT = 587
    settings.SMTP_USE_TLS = True
    settings.SMTP_USERNAME = "user"
    settings.SMTP_PASSWORD = "pass"
    settings.SMTP_FROM_EMAIL = "noreply@test.com"
    settings.FRONTEND_URL = "http://localhost:3000"
    mock_settings.return_value = settings
    server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = server

    send_email_notification(to_email="user@test.com", subject="Hi", body="Body")
    server.starttls.assert_called_once()
    server.login.assert_called_once()
    server.send_message.assert_called_once()
    settings = MagicMock()
    settings.SMTP_HOST = ""
    settings.FRONTEND_URL = "http://localhost:3000"
    mock_settings.return_value = settings
    send_email_notification(to_email="user@test.com", subject="Hi", body="Body", link="/chat")


@patch("app.services.agent_scheduler_service._get_agent_queue", return_value=None)
def test_enqueue_agent_run_without_redis(mock_queue):
    assert enqueue_agent_run(1, run_at=datetime.utcnow()) is None
    assert enqueue_agent_run_now(2) is None


@patch("app.services.agent_scheduler_service._get_agent_queue")
def test_enqueue_agent_run_with_redis(mock_get_queue):
    queue = MagicMock()
    job = MagicMock(id="job-1")
    queue.enqueue_at.return_value = job
    queue.enqueue.return_value = job
    mock_get_queue.return_value = queue

    assert enqueue_agent_run(3, run_at=datetime.utcnow()) == "job-1"
    assert enqueue_agent_run_now(4) == "job-1"


@patch("app.connectors.notion.httpx.post")
@patch("app.connectors.notion.httpx.get")
def test_notion_connector_connect_and_sync(mock_get, mock_post, db_session):
    user = UserFactory()
    search_response = MagicMock()
    search_response.raise_for_status.return_value = None
    search_response.json.return_value = {
        "results": [
            {
                "object": "page",
                "id": "page-1",
                "properties": {"Name": {"type": "title", "title": [{"plain_text": "Page One"}]}},
            }
        ]
    }
    blocks_response = MagicMock()
    blocks_response.raise_for_status.return_value = None
    blocks_response.json.return_value = {
        "results": [{"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Hello Notion"}]}}]
    }
    mock_post.return_value = search_response
    mock_get.return_value = blocks_response

    with patch("app.connectors.notion.index_connector_text") as mock_index:
        with patch("app.connectors.notion.ensure_connector_collection") as mock_collection:
            collection = MagicMock(id=99)
            mock_collection.return_value = collection
            row = save_connection(
                db_session,
                user_id=user.id,
                connector_type="notion",
                credentials={"api_token": "secret-token"},
            )
            assert row.connector_type == "notion"
            assert row.status == "connected"

            result = sync_connector(db_session, user_id=user.id, connector_type="notion")
            assert result["files_synced"] == 1
            mock_index.assert_called_once()


@patch("app.connectors.confluence.httpx.get")
def test_confluence_connector_connect(mock_get, db_session):
    user = UserFactory()
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"results": []}
    mock_get.return_value = response

    row = save_connection(
        db_session,
        user_id=user.id,
        connector_type="confluence",
        credentials={
            "base_url": "https://example.atlassian.net",
            "email": user.email,
            "api_token": "secret-token",
        },
    )
    assert row.connector_type == "confluence"


@patch("app.services.github_connector_service.save_connection")
def test_github_connector_connect(mock_save, db_session):
    user = UserFactory()
    row = save_connection(
        db_session,
        user_id=user.id,
        connector_type="github",
        credentials={"access_token": "gh-token", "github_login": "octo"},
    )
    assert row.connector_type == "github"
    mock_save.assert_called_once()


@patch("app.connectors.google_drive.httpx.get")
def test_google_drive_connector_connect(mock_get, db_session):
    user = UserFactory()
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"files": []}
    mock_get.return_value = response

    row = save_connection(
        db_session,
        user_id=user.id,
        connector_type="google_drive",
        credentials={"access_token": "drive-token"},
    )
    assert row.connector_type == "google_drive"


@patch("app.connectors.dropbox.httpx.post")
def test_dropbox_connector_connect(mock_post, db_session):
    user = UserFactory()
    response = MagicMock()
    response.raise_for_status.return_value = None
    mock_post.return_value = response

    row = save_connection(
        db_session,
        user_id=user.id,
        connector_type="dropbox",
        credentials={"access_token": "dropbox-token"},
    )
    assert row.connector_type == "dropbox"


def test_get_connection_status(db_session):
    user = UserFactory()
    db_session.add(
        ConnectorConnection(
            user_id=user.id,
            connector_type="notion",
            display_name="Notion",
            credentials_encrypted="enc",
            status="connected",
            document_count=3,
        )
    )
    db_session.commit()
    status = get_connection_status(db_session, user_id=user.id)
    notion = next(item for item in status if item["id"] == "notion")
    assert notion["connected"] is True
    assert notion["document_count"] == 3


def test_serialize_connection(db_session):
    user = UserFactory()
    row = ConnectorConnection(
        user_id=user.id,
        connector_type="notion",
        display_name="Notion",
        credentials_encrypted="enc",
        status="connected",
    )
    db_session.add(row)
    db_session.commit()
    payload = serialize_connection(row)
    assert payload["connector_type"] == "notion"


@patch("app.connectors.base.BaseConnector.disconnect")
def test_disconnect_connector(mock_disconnect, db_session):
    user = UserFactory()
    row = ConnectorConnection(
        user_id=user.id,
        connector_type="notion",
        display_name="Notion",
        credentials_encrypted="enc",
        status="connected",
    )
    db_session.add(row)
    db_session.commit()
    assert disconnect_connector(db_session, user_id=user.id, connector_type="notion") is True
    mock_disconnect.assert_called_once()


def test_sync_connector_failure(db_session):
    user = UserFactory()
    with patch("app.connectors.notion.httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"results": []}
        mock_post.return_value = mock_resp
        save_connection(
            db_session,
            user_id=user.id,
            connector_type="notion",
            credentials={"api_token": "token"},
        )

    with patch("app.connectors.notion.NotionConnector.sync", side_effect=RuntimeError("sync failed")):
        with pytest.raises(RuntimeError, match="sync failed"):
            sync_connector(db_session, user_id=user.id, connector_type="notion")


def test_list_connections(db_session):
    user = UserFactory()
    with patch("app.connectors.notion.httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"results": []}
        mock_post.return_value = mock_resp
        save_connection(
            db_session,
            user_id=user.id,
            connector_type="notion",
            credentials={"api_token": "x"},
        )
        rows = list_connections(db_session, user_id=user.id)
    assert len(rows) == 1
