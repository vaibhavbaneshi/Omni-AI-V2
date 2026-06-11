"""Tests for multi_document_service."""

from unittest.mock import MagicMock, patch

from app.services.multi_document_service import (
    group_sources_by_document,
    is_multi_document_query,
    retrieve_multi_document_context,
    should_use_multi_document_analysis,
)
from tests.factories import ChatSessionFactory, UserFactory


def test_is_multi_document_query_detects_comparison():
    assert is_multi_document_query("Compare both documents side by side")
    assert not is_multi_document_query("What is machine learning?")


def test_group_sources_by_document():
    sources = [
        {"source": "a.pdf", "metadata": {"document_id": "1"}},
        {"source": "b.pdf", "metadata": {"document_id": "2"}},
        {"source": "a.pdf", "metadata": {"document_id": "1"}},
    ]
    grouped = group_sources_by_document(sources)
    assert len(grouped["1"]) == 2
    assert len(grouped["2"]) == 1


@patch("app.services.multi_document_service.count_session_documents", return_value=2)
def test_should_use_multi_document_analysis(mock_count, db_session):
    user = UserFactory()
    session = ChatSessionFactory(user=user)
    assert should_use_multi_document_analysis(
        db_session,
        user_id=user.id,
        session_id=session.id,
        query="Compare both documents",
    )
    mock_count.assert_called_once()


@patch("app.services.multi_document_service.count_session_documents", return_value=1)
def test_should_use_multi_document_analysis_requires_two_docs(mock_count, db_session):
    user = UserFactory()
    session = ChatSessionFactory(user=user)
    assert not should_use_multi_document_analysis(
        db_session,
        user_id=user.id,
        session_id=session.id,
        query="Compare both documents",
    )


@patch("app.services.multi_document_service.list_session_documents")
def test_retrieve_multi_document_context_empty_with_single_doc(mock_list, db_session):
    user = UserFactory()
    session = ChatSessionFactory(user=user)
    doc = MagicMock()
    doc.id = 1
    doc.filename = "only.pdf"
    mock_list.return_value = [doc]

    result = retrieve_multi_document_context(
        db=db_session,
        user_id=user.id,
        session_id=session.id,
        query="compare documents",
    )
    assert result["context"] == ""
    assert result["sources"] == []


@patch("app.services.multi_document_service.rerank_documents", side_effect=lambda **kwargs: kwargs["documents"][: kwargs["top_k"]])
@patch("app.services.documents_services.get_document_collection")
@patch("app.services.multi_document_service.list_session_documents")
def test_retrieve_multi_document_context_groups_documents(
    mock_list,
    mock_collection,
    mock_rerank,
    db_session,
):
    user = UserFactory()
    session = ChatSessionFactory(user=user)

    doc_a = MagicMock(id=1, filename="alpha.pdf")
    doc_b = MagicMock(id=2, filename="beta.pdf")
    mock_list.return_value = [doc_a, doc_b]

    chroma = MagicMock()
    chroma.get.side_effect = [
        {"documents": ["chunk a1", "chunk a2"], "metadatas": [{}, {}]},
        {"documents": ["chunk b1"], "metadatas": [{}]},
    ]
    mock_collection.return_value = chroma

    result = retrieve_multi_document_context(
        db=db_session,
        user_id=user.id,
        session_id=session.id,
        query="compare alpha and beta",
    )

    assert result["strategy"] == "multi-document"
    assert result["chunks"] >= 2
    assert "alpha.pdf" in result["context"]
    assert "beta.pdf" in result["context"]
    assert len(result["document_groups"]) == 2


@patch("app.services.documents_services.get_document_collection")
@patch("app.services.multi_document_service.list_session_documents")
def test_retrieve_multi_document_context_handles_chroma_failure(
    mock_list,
    mock_collection,
    db_session,
):
    user = UserFactory()
    session = ChatSessionFactory(user=user)
    doc_a = MagicMock(id=1, filename="fail.pdf")
    doc_b = MagicMock(id=2, filename="ok.pdf")
    mock_list.return_value = [doc_a, doc_b]

    chroma = MagicMock()
    chroma.get.side_effect = [Exception("chroma down"), {"documents": ["ok chunk"], "metadatas": [{}]}]
    mock_collection.return_value = chroma

    result = retrieve_multi_document_context(
        db=db_session,
        user_id=user.id,
        session_id=session.id,
        query="compare documents",
    )
    assert result["strategy"] == "multi-document"
    assert result["chunks"] >= 1
