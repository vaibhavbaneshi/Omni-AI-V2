"""Tests for knowledge graph service (Phase I)."""

from app.models.document_entity import DocumentEntity
from app.models.knowledge_graph import GraphEdge, GraphNode
from app.services.knowledge_graph_service import (
    build_workspace_graph,
    get_document_graph,
    graph_rag_context,
    search_graph,
)
from tests.factories import UserFactory


def test_build_workspace_graph_from_entities(db_session):
    from app.models.document import DocumentCollection, DocumentRecord

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

    db_session.add(
        DocumentEntity(
            document_id=document.id,
            user_id=user.id,
            name="Omni AI",
            entity_type="organization",
            mentions=2,
            context="Omni AI partners with Acme Corp in 2024.",
        )
    )
    db_session.add(
        DocumentEntity(
            document_id=document.id,
            user_id=user.id,
            name="Acme Corp",
            entity_type="organization",
            mentions=1,
            context="Acme Corp works at enterprise scale.",
        )
    )
    db_session.commit()

    stats = build_workspace_graph(
        db_session,
        user_id=user.id,
        workspace_id="default",
        document_id=document.id,
    )
    assert stats["entity_rows"] == 2
    assert db_session.query(GraphNode).count() >= 2
    assert db_session.query(GraphEdge).count() >= 1

    graph = get_document_graph(db_session, user_id=user.id, document_id=document.id)
    assert len(graph["nodes"]) >= 2
    assert graph["document_id"] == document.id

    search = search_graph(db_session, user_id=user.id, query="Omni", workspace_id="default")
    assert any(node["name"] == "Omni AI" for node in search["nodes"])

    context = graph_rag_context(
        db_session,
        user_id=user.id,
        query="Omni AI partnerships",
        workspace_id="default",
    )
    assert "Knowledge graph context" in context
    assert "Omni AI" in context
