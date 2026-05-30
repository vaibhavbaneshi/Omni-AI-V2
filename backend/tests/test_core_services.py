"""Unit tests for core utilities and services."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.sanitize import sanitize_retrieved_context, sanitize_user_query
from app.core.upload_validation import validate_document_upload
from app.services.conversation_service import get_chat_history
from app.services.session_service import delete_chat_session
from tests.factories import ChatSessionFactory, MessageFactory, UserFactory


def test_sanitize_user_query_truncates():
    result = sanitize_user_query("  hello world  ", max_length=100)
    assert result == "hello world"


def test_sanitize_retrieved_context_strips_noise():
    chunks = ["  valid chunk  ", "", "second chunk"]
    result = sanitize_retrieved_context(chunks)
    assert "valid chunk" in result
    assert "second chunk" in result


@pytest.mark.asyncio
async def test_validate_document_upload_rejects_empty_file():
    class _Upload:
        filename = "empty.txt"
        content_type = "text/plain"

        async def read(self, size: int = -1):
            return b"   "

        async def seek(self, pos: int):
            return None

    with pytest.raises(Exception) as exc:
        await validate_document_upload(_Upload(), max_bytes=1024)
    assert exc.value.status_code == 400


def test_get_chat_history_respects_limit(db_session):
    session = ChatSessionFactory()
    for index in range(10):
        MessageFactory(session=session, role="user", content=f"msg-{index}")
    db_session.commit()

    with patch("app.services.conversation_service.SessionLocal") as mock_session_local:
        db_session.close = lambda: None
        mock_session_local.return_value = db_session
        history = get_chat_history(session.id, user_id=session.user_id, limit=3)

    assert history.count("user:") == 3


@patch("app.services.session_service.chroma_collection")
def test_delete_chat_session_removes_messages(mock_chroma, db_session):
    mock_chroma.get.return_value = {"ids": []}
    session = ChatSessionFactory()
    MessageFactory(session=session, role="user", content="delete me")

    deleted = delete_chat_session(
        db_session,
        user_id=session.user_id,
        session_id=session.id,
    )
    assert deleted is True
    assert db_session.query(MessageFactory._meta.model).filter_by(session_id=session.id).count() == 0
