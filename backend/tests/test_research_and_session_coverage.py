"""Coverage for research modules, session service, and search service."""

import json
from unittest.mock import MagicMock, patch

from app.research.contradiction import detect_contradictions
from app.research.multi_hop import multi_hop_retrieval
from app.research.verification import verify_sources
from app.services.search_service import global_search
from app.services.session_service import DeleteSessionResult, delete_chat_session
from tests.factories import ChatSessionFactory, UserFactory


@patch("app.research.verification.invoke_generate", return_value='{"confidence_score": 0.8, "supported_claims": ["A"]}')
def test_verify_sources_parses_json(mock_invoke):
    result = verify_sources(query="Q", evidence="Evidence text", sources=[{"label": "S1"}])
    assert result["confidence_score"] == 0.8
    mock_invoke.assert_called_once()


@patch("app.research.verification.invoke_generate", return_value="not json")
def test_verify_sources_fallback(mock_invoke):
    result = verify_sources(query="Q", evidence="Evidence", sources=[])
    assert result["confidence_score"] == 0.5


@patch("app.research.contradiction.invoke_generate", return_value='{"contradictions": [], "consistent_themes": ["A"]}')
def test_detect_contradictions(mock_invoke):
    result = detect_contradictions(query="Q", evidence="Evidence")
    assert result["consistent_themes"] == ["A"]


@patch("app.research.contradiction.invoke_generate", return_value="broken")
def test_detect_contradictions_fallback(mock_invoke):
    result = detect_contradictions(query="Q", evidence="Evidence")
    assert result["contradictions"] == []


@patch("app.research.multi_hop._collect_evidence")
def test_multi_hop_retrieval(mock_collect):
    mock_collect.return_value = (["chunk"], ["source"], ["label"], [{"id": 1}], [{"step": 1}])
    chunks, sources, labels, source_dicts, traces = multi_hop_retrieval(
        plan={"search_queries": ["q1", "q2"]},
        user_id=1,
        workspace_id="default",
        collection_id=None,
        session_id=1,
        max_iterations=2,
    )
    assert chunks
    assert len(traces) == 2


def test_delete_chat_session_not_found(db_session):
    user = UserFactory()
    result = delete_chat_session(db_session, user_id=user.id, session_id=99999)
    assert result == DeleteSessionResult.NOT_FOUND


@patch("app.services.session_service.get_document_collection")
def test_delete_chat_session_success(mock_chroma, db_session):
    user = UserFactory()
    session = ChatSessionFactory(user=user, title="Delete me")
    chroma = MagicMock()
    chroma.get.return_value = {"ids": []}
    mock_chroma.return_value = chroma

    result = delete_chat_session(db_session, user_id=user.id, session_id=session.id)
    assert result == DeleteSessionResult.DELETED


def test_global_search_short_query(db_session):
    user = UserFactory()
    result = global_search(db_session, user_id=user.id, query="a")
    assert result["results"] == []


def test_global_search_finds_session(db_session):
    user = UserFactory()
    ChatSessionFactory(user=user, title="UniqueAlphaSessionTitle")
    result = global_search(db_session, user_id=user.id, query="UniqueAlpha")
    assert any(item["type"] == "session" for item in result["results"])


def test_global_search_document_source_filter(db_session):
    from app.models.document import DocumentCollection, DocumentRecord

    user = UserFactory()
    collection = DocumentCollection(user_id=user.id, workspace_id="default", name="GitHub Sync")
    db_session.add(collection)
    db_session.commit()
    db_session.add(
        DocumentRecord(
            user_id=user.id,
            workspace_id="default",
            collection_id=collection.id,
            filename="github-readme.md",
            storage_path="/tmp/github-readme.md",
            file_size=10,
        )
    )
    db_session.commit()

    result = global_search(db_session, user_id=user.id, query="github-readme", source="GitHub")
    assert any(item["type"] == "document" for item in result["results"])


def test_global_search_finds_message_snippet(db_session):
    user = UserFactory()
    session = ChatSessionFactory(user=user, title="Snippet chat")
    from app.models.message import Message

    long_content = "UniqueBetaToken " + ("word " * 80)
    db_session.add(Message(session_id=session.id, user_id=user.id, role="user", content=long_content))
    db_session.commit()

    result = global_search(db_session, user_id=user.id, query="UniqueBetaToken")
    assert any(item["type"] == "message" for item in result["results"])
    message = next(item for item in result["results"] if item["type"] == "message")
    assert message["snippet"].endswith("…")
