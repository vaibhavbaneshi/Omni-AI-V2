"""Tests for document intelligence service and API."""

import json
from unittest.mock import patch

from tests.factories import ChatSessionFactory, UserFactory


SAMPLE_PAYLOAD = {
    "executive_summary": {
        "overview": "This document covers quarterly revenue growth.",
        "key_findings": ["Revenue increased 12%"],
        "important_points": ["North America led growth"],
        "risks": ["Supply chain delays"],
        "recommendations": ["Expand APAC sales"],
    },
    "faqs": [{"question": "What was revenue growth?", "answer": "12% year over year."}],
    "action_items": [{"task": "Review APAC plan", "deadline": "2026-07-01", "owner": "Sales"}],
    "metadata_insights": {
        "keywords": ["revenue", "growth"],
        "topics": ["Finance"],
        "entities": ["North America"],
        "important_dates": ["Q1 2026"],
        "statistics": ["12% growth"],
    },
}


def test_load_document_text_falls_back_to_indexed_chunks(db_session, monkeypatch):
    from app.models.document import DocumentCollection, DocumentRecord
    from app.services.document_intelligence_service import _load_document_text

    user = UserFactory()
    collection = DocumentCollection(user_id=user.id, workspace_id="default", name="Default")
    db_session.add(collection)
    db_session.commit()

    document = DocumentRecord(
        user_id=user.id,
        workspace_id="default",
        collection_id=collection.id,
        filename="report.docx",
        storage_path="/data/uploads/missing/report.docx",
        file_size=128,
        chunks_created=2,
        indexing_stage="ready",
    )
    db_session.add(document)
    db_session.commit()

    class FakeCollection:
        def get(self, **_kwargs):
            return {
                "documents": ["Chunk one text.", "Chunk two text."],
                "metadatas": [{"chunk_index": 0}, {"chunk_index": 1}],
            }

    monkeypatch.setattr(
        "app.services.documents_services.get_document_collection",
        lambda: FakeCollection(),
    )

    text = _load_document_text(db_session, document)
    assert "Chunk one text." in text
    assert "Chunk two text." in text


@patch("app.services.document_intelligence_service._load_document_text")
@patch("app.services.document_intelligence_service.invoke_generate")
def test_generate_document_insights_persists_payload(
    mock_invoke,
    mock_load_text,
    db_session,
):
    from app.models.document import DocumentCollection, DocumentRecord
    from app.services.document_intelligence_service import generate_document_insights

    user = UserFactory()
    session = ChatSessionFactory(user=user)
    collection = DocumentCollection(user_id=user.id, workspace_id="default", name="Default")
    db_session.add(collection)
    db_session.commit()

    document = DocumentRecord(
        user_id=user.id,
        workspace_id="default",
        collection_id=collection.id,
        session_id=session.id,
        filename="report.txt",
        storage_path="/tmp/report.txt",
        file_size=128,
        chunks_created=4,
        indexing_stage="ready",
    )
    db_session.add(document)
    db_session.commit()

    mock_load_text.return_value = "Quarterly revenue increased 12 percent."
    mock_invoke.return_value = json.dumps(SAMPLE_PAYLOAD)

    record = generate_document_insights(
        db_session,
        user_id=user.id,
        document_id=document.id,
    )

    assert record.status == "ready"
    assert record.payload["executive_summary"]["overview"].startswith("This document")
    assert len(record.payload["faqs"]) == 1
    assert len(record.payload["action_items"]) == 1


@patch("app.services.document_intelligence_service._load_document_text")
@patch("app.services.document_intelligence_service.invoke_generate")
def test_document_insights_api(
    mock_invoke,
    mock_load_text,
    auth_client,
    db_session,
):
    from app.models.document import DocumentCollection, DocumentRecord

    collection = DocumentCollection(
        user_id=auth_client.auth_user.id,
        workspace_id="default",
        name="Default",
    )
    db_session.add(collection)
    db_session.commit()

    session = ChatSessionFactory(user=auth_client.auth_user)
    document = DocumentRecord(
        user_id=auth_client.auth_user.id,
        workspace_id="default",
        collection_id=collection.id,
        session_id=session.id,
        filename="notes.txt",
        storage_path="/tmp/notes.txt",
        file_size=64,
        chunks_created=2,
        indexing_stage="ready",
    )
    db_session.add(document)
    db_session.commit()

    mock_load_text.return_value = "Project milestones and deadlines for Q3."
    mock_invoke.return_value = json.dumps(SAMPLE_PAYLOAD)

    response = auth_client.post(
        f"/documents/{document.id}/insights/generate",
        headers=auth_client.auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ready"

    fetched = auth_client.get(
        f"/documents/{document.id}/insights",
        headers=auth_client.auth_headers,
    )
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["payload"]["executive_summary"]["overview"]
