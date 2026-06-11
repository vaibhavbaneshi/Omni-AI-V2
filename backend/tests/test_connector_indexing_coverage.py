"""Coverage for connector indexing helpers."""

from unittest.mock import patch

from app.connectors.indexing import ensure_connector_collection, index_connector_text
from app.models.document import DocumentCollection, DocumentRecord
from tests.factories import UserFactory


def test_ensure_connector_collection_creates_and_reuses(db_session):
    user = UserFactory()
    first = ensure_connector_collection(
        db_session,
        user_id=user.id,
        workspace_id="default",
        name="Notion",
    )
    second = ensure_connector_collection(
        db_session,
        user_id=user.id,
        workspace_id="default",
        name="Notion",
    )
    assert first.id == second.id


@patch("app.services.ingestion_service.run_ingest_document_record")
def test_index_connector_text_creates_document(mock_ingest, db_session):
    user = UserFactory()
    collection = DocumentCollection(user_id=user.id, workspace_id="default", name="Hub")
    db_session.add(collection)
    db_session.commit()

    document = index_connector_text(
        db_session,
        user=user,
        collection_id=collection.id,
        workspace_id="default",
        source_key="abc",
        filename="notion__abc.md",
        text="Connector content",
    )
    assert document.filename == "notion__abc.md"
    mock_ingest.assert_called_once()


@patch("app.services.ingestion_service.run_ingest_document_record")
def test_index_connector_text_updates_existing(mock_ingest, db_session, tmp_path):
    user = UserFactory()
    collection = DocumentCollection(user_id=user.id, workspace_id="default", name="Hub")
    db_session.add(collection)
    db_session.commit()

    storage_path = tmp_path / "existing.txt"
    storage_path.write_text("old", encoding="utf-8")
    existing = DocumentRecord(
        user_id=user.id,
        workspace_id="default",
        collection_id=collection.id,
        filename="notion__abc.md",
        storage_path=str(storage_path),
        file_size=3,
        indexing_stage="ready",
    )
    db_session.add(existing)
    db_session.commit()

    document = index_connector_text(
        db_session,
        user=user,
        collection_id=collection.id,
        workspace_id="default",
        source_key="abc",
        filename="notion__abc.md",
        text="Updated connector content",
    )
    assert document.id == existing.id
    assert storage_path.read_text(encoding="utf-8") == "Updated connector content"
