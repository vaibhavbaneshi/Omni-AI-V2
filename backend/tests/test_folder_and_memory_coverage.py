"""Coverage for folder and memory summary services."""

from unittest.mock import patch

import pytest

from app.models.chat_folder import ChatFolder
from app.models.conversation_summary import ConversationSummary
from app.models.message import Message
from app.services.folder_service import (
    create_folder,
    delete_folder,
    list_folders,
    update_folder,
    update_session_organization,
)
from app.services.memory_summary_service import generate_summary, get_summary
from tests.factories import ChatSessionFactory, UserFactory


def test_folder_service_crud(db_session):
    user = UserFactory()
    folder = create_folder(db_session, user_id=user.id, name="Work")
    assert folder.name == "Work"

    folders = list_folders(db_session, user_id=user.id)
    assert folders[0]["session_count"] == 0

    updated = update_folder(db_session, user_id=user.id, folder_id=folder.id, name="Projects")
    assert updated is not None
    assert updated.name == "Projects"


def test_create_folder_requires_name(db_session):
    user = UserFactory()
    with pytest.raises(ValueError, match="required"):
        create_folder(db_session, user_id=user.id, name="  ")


@patch("app.services.memory_summary_service.SessionLocal")
def test_generate_summary_creates_row(mock_session_local, db_session):
    user = UserFactory()
    session = ChatSessionFactory(user=user)
    session_id = session.id
    db_session.add(
        Message(session_id=session_id, user_id=user.id, role="user", content="Hello there")
    )
    db_session.commit()
    mock_session_local.return_value = db_session

    generate_summary(session_id)
    row = db_session.query(ConversationSummary).filter(ConversationSummary.session_id == session_id).first()
    assert row is not None
    assert "Hello there" in row.summary


@patch("app.services.memory_summary_service.SessionLocal")
def test_get_summary_returns_empty_when_missing(mock_session_local, db_session):
    mock_session_local.return_value = db_session
    assert get_summary(999999) == ""


def test_delete_folder_and_session_organization(db_session):
    user = UserFactory()
    folder = create_folder(db_session, user_id=user.id, name="Archive")
    session = ChatSessionFactory(user=user)
    updated = update_session_organization(
        db_session,
        user_id=user.id,
        session_id=session.id,
        folder_id=folder.id,
        is_pinned=True,
    )
    assert updated is not None
    assert updated.folder_id == folder.id
    assert delete_folder(db_session, user_id=user.id, folder_id=folder.id) is True
