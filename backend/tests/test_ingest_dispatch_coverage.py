"""Additional ingestion queue dispatch coverage."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.app_settings import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@patch("app.services.ingestion_queue.run_ingest_inline_thread")
@patch("app.services.ingestion_queue.get_active_worker_count", return_value=0)
def test_dispatch_documents_ingestion_inline_fallback(mock_workers, mock_inline, db_session):
    from app.services.ingestion_queue import dispatch_documents_ingestion

    result = dispatch_documents_ingestion(db_session, [101, 102])
    assert result["dispatch"] == "inline_thread"
    assert result["queued"] == 2
    assert mock_inline.call_count == 2


@patch("app.services.ingestion_queue.enqueue_documents_ingestion", return_value=2)
@patch("app.services.ingestion_queue.get_active_worker_count", return_value=1)
def test_dispatch_documents_ingestion_rq(mock_workers, mock_enqueue, db_session):
    from app.services.ingestion_queue import dispatch_documents_ingestion

    result = dispatch_documents_ingestion(db_session, [101, 102])
    assert result["dispatch"] == "rq"
    assert result["queued"] == 2


def test_dispatch_documents_ingestion_empty(db_session):
    from app.services.ingestion_queue import dispatch_documents_ingestion

    result = dispatch_documents_ingestion(db_session, [])
    assert result["dispatch"] == "none"


def test_ingest_queue_enabled(monkeypatch):
    monkeypatch.setenv("INGEST_IN_BACKGROUND", "true")
    monkeypatch.setenv("INGEST_QUEUE_ENABLED", "true")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    get_settings.cache_clear()

    from app.services.ingestion_queue import ingest_queue_enabled, should_use_background_tasks

    assert ingest_queue_enabled() is True
    assert should_use_background_tasks() is False


@patch("app.services.github_connector_service.sync_repository", return_value={"files_indexed": 2, "status": "complete"})
@patch("app.services.github_connector_service.list_repositories", return_value=[{"full_name": "octo/repo"}])
def test_github_connector_sync(mock_repos, mock_sync, db_session):
    from app.connectors.github import GitHubConnector
    from app.models.connector_hub import ConnectorConnection
    from tests.factories import UserFactory

    user = UserFactory()
    connection = ConnectorConnection(
        user_id=user.id,
        connector_type="github",
        display_name="GitHub",
        credentials_encrypted="enc",
        status="connected",
        connection_metadata={"github_login": "octo"},
    )
    db_session.add(connection)
    db_session.commit()

    result = GitHubConnector().sync(db_session, connection=connection)
    assert result["files_indexed"] == 2


@patch("app.connectors.confluence.httpx.get")
def test_confluence_connector_sync(mock_get, db_session):
    from app.connectors.confluence import ConfluenceConnector
    from app.core.credential_crypto import encrypt_credentials
    from app.models.connector_hub import ConnectorConnection
    from tests.factories import UserFactory

    user = UserFactory()
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "results": [
            {
                "id": "1",
                "title": "Page",
                "body": {"storage": {"value": "<p>Confluence content</p>"}},
            }
        ]
    }
    mock_get.return_value = response

    connection = ConnectorConnection(
        user_id=user.id,
        connector_type="confluence",
        display_name="Confluence",
        credentials_encrypted=encrypt_credentials(
            {
                "base_url": "https://example.atlassian.net",
                "email": user.email,
                "api_token": "token",
            }
        ),
        status="connected",
        connection_metadata={"base_url": "https://example.atlassian.net"},
    )
    db_session.add(connection)
    db_session.commit()

    with patch("app.connectors.confluence.index_connector_text") as mock_index:
        with patch("app.connectors.confluence.ensure_connector_collection") as mock_collection:
            mock_collection.return_value = MagicMock(id=1)
            result = ConfluenceConnector().sync(db_session, connection=connection)
    assert result["files_synced"] == 1
    mock_index.assert_called_once()


@patch("app.connectors.google_drive.httpx.get")
def test_google_drive_connector_sync(mock_get, db_session):
    from app.connectors.google_drive import GoogleDriveConnector
    from app.core.credential_crypto import encrypt_credentials
    from app.models.connector_hub import ConnectorConnection
    from tests.factories import UserFactory

    user = UserFactory()
    list_response = MagicMock()
    list_response.raise_for_status.return_value = None
    list_response.json.return_value = {
        "files": [{"id": "file-1", "name": "Notes.txt", "mimeType": "text/plain"}]
    }
    download_response = MagicMock()
    download_response.raise_for_status.return_value = None
    download_response.content = b"Drive file content"
    mock_get.side_effect = [list_response, download_response]

    connection = ConnectorConnection(
        user_id=user.id,
        connector_type="google_drive",
        display_name="Drive",
        credentials_encrypted=encrypt_credentials({"access_token": "drive-token"}),
        status="connected",
    )
    db_session.add(connection)
    db_session.commit()

    with patch("app.connectors.google_drive.index_connector_text") as mock_index:
        with patch("app.connectors.google_drive.ensure_connector_collection") as mock_collection:
            mock_collection.return_value = MagicMock(id=1)
            result = GoogleDriveConnector().sync(db_session, connection=connection)
    assert result["files_synced"] == 1
    mock_index.assert_called_once()
