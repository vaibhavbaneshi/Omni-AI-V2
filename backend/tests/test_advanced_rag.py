"""Tests for Phase B advanced RAG features."""

from unittest.mock import patch

from app.services.query_contextualizer_service import (
    contextualize_query,
    needs_contextualization,
    resolve_retrieval_query,
)


def test_needs_contextualization_detects_followups():
    history = "user: Summarize the quarterly report\nassistant: Revenue grew 12%."
    assert needs_contextualization("Expand point 3", history)
    assert needs_contextualization("What about that?", history)
    assert not needs_contextualization("", history)
    assert not needs_contextualization(
        "Compare LangChain versus LangGraph for agent workflows",
        history,
    )


def test_contextualize_query_heuristic_fallback():
    history = "user: Explain our refund policy\nassistant: Refunds are allowed within 14 days."
    result = contextualize_query(
        "Tell me more about that",
        history=history,
    )
    assert "refund" in result.lower()


@patch("app.services.query_contextualizer_service.invoke_generate")
def test_contextualize_query_uses_llm_when_enabled(mock_invoke):
    mock_invoke.return_value = "Explain the refund policy timeline and exceptions"
    history = "user: Explain our refund policy\nassistant: Refunds are allowed within 14 days."

    result = contextualize_query("Tell me more about that", history=history)

    assert result.startswith("Explain the refund policy")
    mock_invoke.assert_called_once()


def test_resolve_retrieval_query_returns_original_when_unchanged():
    retrieval_query, original = resolve_retrieval_query(
        "What is vector search?",
        history="",
    )
    assert retrieval_query == "What is vector search?"
    assert original is None


def test_is_multi_document_query():
    from app.services.multi_document_service import is_multi_document_query

    assert is_multi_document_query("Compare the two uploaded PDFs")
    assert is_multi_document_query("What is the difference between these documents?")
    assert not is_multi_document_query("Summarize the attached file")


def test_group_sources_by_document():
    from app.services.multi_document_service import group_sources_by_document

    sources = [
        {"source": "a.pdf", "metadata": {"document_id": "10"}},
        {"source": "b.pdf", "metadata": {"document_id": "11"}},
        {"source": "a.pdf", "metadata": {"document_id": "10"}},
    ]
    grouped = group_sources_by_document(sources)
    assert len(grouped["10"]) == 2
    assert len(grouped["11"]) == 1


def test_should_use_multi_document_analysis(db_session):
    from app.services.multi_document_service import should_use_multi_document_analysis
    from tests.factories import ChatSessionFactory, UserFactory
    from app.models.document import DocumentCollection, DocumentRecord

    user = UserFactory()
    session = ChatSessionFactory(user=user)
    collection = DocumentCollection(user_id=user.id, workspace_id="default", name="Default")
    db_session.add(collection)
    db_session.commit()

    for index, name in enumerate(("alpha.pdf", "beta.pdf"), start=1):
        db_session.add(
            DocumentRecord(
                user_id=user.id,
                workspace_id="default",
                collection_id=collection.id,
                session_id=session.id,
                filename=name,
                storage_path=f"/tmp/{name}",
                file_size=128,
                chunks_created=2,
                indexing_stage="ready",
            )
        )
    db_session.commit()

    assert should_use_multi_document_analysis(
        db_session,
        user_id=user.id,
        session_id=session.id,
        query="Compare both documents",
    )
    assert not should_use_multi_document_analysis(
        db_session,
        user_id=user.id,
        session_id=session.id,
        query="Summarize the attached file",
    )


def test_hybrid_search_ranked_merges_semantic_and_bm25():
    from app.services import hybrid_search as hybrid_module

    with patch.object(hybrid_module, "semantic_search", return_value=["doc-a", "doc-b"]), patch.object(
        hybrid_module,
        "bm25_search_ranked",
        return_value=[("doc-b", 1.5), ("doc-c", 1.0)],
    ):
        ranked = hybrid_module.hybrid_search_ranked("test query", top_k=3, user_id=1)
        documents = [doc for doc, _ in ranked]

    assert documents[0] == "doc-b"
    assert set(documents) == {"doc-a", "doc-b", "doc-c"}


def test_orchestrator_routes_multi_document_analysis(db_session):
    from tests.factories import ChatSessionFactory, UserFactory
    from app.agent.orchestrator import AgentOrchestrator
    from app.models.document import DocumentCollection, DocumentRecord

    user = UserFactory()
    session = ChatSessionFactory(user=user)
    collection = DocumentCollection(user_id=user.id, workspace_id="default", name="Default")
    db_session.add(collection)
    db_session.commit()

    for name in ("one.pdf", "two.pdf"):
        db_session.add(
            DocumentRecord(
                user_id=user.id,
                workspace_id="default",
                collection_id=collection.id,
                session_id=session.id,
                filename=name,
                storage_path=f"/tmp/{name}",
                file_size=64,
                chunks_created=1,
                indexing_stage="ready",
            )
        )
    db_session.commit()

    route = AgentOrchestrator().plan(
        "Compare both uploaded documents",
        mode="research",
        db=db_session,
        user_id=user.id,
        session_id=session.id,
    )

    assert route.strategy == "multi-document-analysis"
    assert "retrieval" in route.tools
