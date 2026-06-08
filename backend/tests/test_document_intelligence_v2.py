from app.schemas.document_insight_schemas import (
    DocumentInsightPayload,
    DocumentMetadataInsights,
    StructuredEntity,
    TimelineEvent,
)
from app.services.document_intelligence_service import _persist_timeline_and_entities


def test_persist_timeline_and_entities(db_session):
    from app.models.document import DocumentCollection, DocumentRecord
    from app.models.document_entity import DocumentEntity
    from app.models.document_timeline import DocumentTimeline
    from tests.factories import UserFactory

    user = UserFactory()
    collection = DocumentCollection(user_id=user.id, workspace_id="default", name="Default")
    db_session.add(collection)
    db_session.commit()

    document = DocumentRecord(
        user_id=user.id,
        workspace_id="default",
        collection_id=collection.id,
        filename="report.pdf",
        storage_path="/tmp/report.pdf",
        file_size=100,
        chunks_created=3,
        indexing_stage="ready",
    )
    db_session.add(document)
    db_session.commit()

    payload = DocumentInsightPayload(
        metadata_insights=DocumentMetadataInsights(
            timeline=[
                TimelineEvent(date="2024-01-01", label="Launch", description="Product launch")
            ],
            structured_entities=[
                StructuredEntity(name="Omni AI", entity_type="organization", mentions=2)
            ],
        )
    )

    _persist_timeline_and_entities(
        db_session,
        document_id=document.id,
        user_id=user.id,
        model_name="test-model",
        payload=payload,
    )
    db_session.commit()

    timeline = db_session.query(DocumentTimeline).filter_by(document_id=document.id).one()
    entities = db_session.query(DocumentEntity).filter_by(document_id=document.id).all()

    assert len(timeline.events) == 1
    assert timeline.events[0]["label"] == "Launch"
    assert len(entities) == 1
    assert entities[0].name == "Omni AI"
