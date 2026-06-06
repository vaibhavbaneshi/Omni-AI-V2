"""Unit tests for Redis + RQ ingestion queue."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.app_settings import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_ingest_uses_rq_queue_when_redis_configured(monkeypatch):
    monkeypatch.setenv("INGEST_QUEUE_ENABLED", "true")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    get_settings.cache_clear()
    assert get_settings().ingest_uses_rq_queue is True


def test_ingest_queue_disabled_without_redis(monkeypatch):
    monkeypatch.setenv("INGEST_QUEUE_ENABLED", "true")
    monkeypatch.setenv("REDIS_URL", "")
    monkeypatch.setenv("REDIS_HOST", "")
    get_settings.cache_clear()
    assert get_settings().ingest_uses_rq_queue is False


@patch("app.services.ingestion_queue.get_ingest_queue")
def test_enqueue_document_ingestion_persists_job_id(mock_get_queue, db_session):
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("INGEST_QUEUE_ENABLED", "true")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    get_settings.cache_clear()

    from app.models.document import DocumentCollection, DocumentRecord
    from app.services.ingestion_queue import enqueue_document_ingestion
    from tests.factories import ChatSessionFactory, UserFactory

    user = UserFactory()
    collection = DocumentCollection(user_id=user.id, workspace_id="default", name="Default")
    db_session.add(collection)
    db_session.flush()
    session = ChatSessionFactory(user=user)

    document = DocumentRecord(
        user_id=user.id,
        collection_id=collection.id,
        session_id=session.id,
        filename="test.txt",
        storage_path="/tmp/test.txt",
        file_size=10,
        indexing_stage="queued",
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)

    mock_job = MagicMock()
    mock_job.id = "ingest-doc-99-test"
    mock_queue = MagicMock()
    mock_queue.enqueue.return_value = mock_job
    mock_get_queue.return_value = mock_queue

    job_id = enqueue_document_ingestion(db_session, document.id)

    assert job_id == "ingest-doc-99-test"
    db_session.refresh(document)
    assert document.indexing_job_id == "ingest-doc-99-test"
    mock_queue.enqueue.assert_called_once()
    enqueue_kwargs = mock_queue.enqueue.call_args.kwargs
    assert enqueue_kwargs["retry"].max == get_settings().INGEST_JOB_MAX_RETRIES
    monkeypatch.undo()


@patch("app.services.ingestion_queue.get_ingest_queue")
@patch("app.services.ingestion_queue.get_dlq")
def test_queue_metrics(mock_dlq, mock_queue, monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    get_settings.cache_clear()

    from app.services.ingestion_queue import get_ingestion_queue_metrics

    main_q = MagicMock()
    main_q.count = 5
    main_q.deferred_job_registry.count = 0
    main_q.scheduled_job_registry.count = 1
    mock_queue.return_value = main_q

    dlq_q = MagicMock()
    dlq_q.count = 2
    mock_dlq.return_value = dlq_q

    with patch("app.services.ingestion_queue.StartedJobRegistry") as started, patch(
        "app.services.ingestion_queue.FailedJobRegistry"
    ) as failed, patch("app.services.ingestion_queue.FinishedJobRegistry") as finished:
        started.return_value.count = 1
        failed.return_value.count = 3
        finished.return_value.count = 10
        metrics = get_ingestion_queue_metrics()

    assert metrics["queue_length"] == 5
    assert metrics["dlq_length"] == 2
    assert metrics["active_jobs"] == 1
    assert metrics["failed_jobs"] == 3
    assert metrics["completed_jobs"] == 10
