"""Tests for notification_service."""

from unittest.mock import patch

from app.services.notification_service import (
    get_unread_count,
    list_notifications,
    mark_all_read,
    mark_notification_read,
    notify_user,
    serialize_notification,
)
from tests.factories import UserFactory


def test_notify_user_stores_notification(db_session):
    user = UserFactory()
    row = notify_user(
        db_session,
        user_id=user.id,
        title="Upload complete",
        body="Your document is ready.",
        category="document",
        link="/chat",
    )
    assert row.id is not None
    assert row.user_id == user.id
    assert row.title == "Upload complete"
    assert row.read is False


def test_list_notifications_returns_user_rows(db_session):
    user = UserFactory()
    other = UserFactory()
    notify_user(db_session, user_id=user.id, title="Mine")
    notify_user(db_session, user_id=other.id, title="Theirs")

    rows = list_notifications(db_session, user_id=user.id)
    assert len(rows) == 1
    assert rows[0].title == "Mine"


def test_list_notifications_empty_when_none(db_session):
    user = UserFactory()
    assert list_notifications(db_session, user_id=user.id) == []


def test_list_notifications_unread_only(db_session):
    user = UserFactory()
    notify_user(db_session, user_id=user.id, title="Unread")
    read_row = notify_user(db_session, user_id=user.id, title="Read me")
    mark_notification_read(db_session, user_id=user.id, notification_id=read_row.id)
    rows = list_notifications(db_session, user_id=user.id, unread_only=True)
    assert len(rows) == 1
    assert rows[0].title == "Unread"


def test_mark_notification_read_updates_status(db_session):
    user = UserFactory()
    row = notify_user(db_session, user_id=user.id, title="Unread")
    assert mark_notification_read(db_session, user_id=user.id, notification_id=row.id) is True
    updated = list_notifications(db_session, user_id=user.id)[0]
    assert updated.read is True


def test_mark_notification_read_returns_false_for_other_user(db_session):
    user = UserFactory()
    other = UserFactory()
    row = notify_user(db_session, user_id=user.id, title="Private")
    assert mark_notification_read(db_session, user_id=other.id, notification_id=row.id) is False


def test_get_unread_count(db_session):
    user = UserFactory()
    notify_user(db_session, user_id=user.id, title="One")
    second = notify_user(db_session, user_id=user.id, title="Two")
    assert get_unread_count(db_session, user_id=user.id) == 2
    mark_notification_read(db_session, user_id=user.id, notification_id=second.id)
    assert get_unread_count(db_session, user_id=user.id) == 1


def test_mark_all_read(db_session):
    user = UserFactory()
    notify_user(db_session, user_id=user.id, title="A")
    notify_user(db_session, user_id=user.id, title="B")
    count = mark_all_read(db_session, user_id=user.id)
    assert count == 2
    assert get_unread_count(db_session, user_id=user.id) == 0


def test_serialize_notification_shape(db_session):
    user = UserFactory()
    row = notify_user(db_session, user_id=user.id, title="Hello", body="World")
    payload = serialize_notification(row)
    assert payload["title"] == "Hello"
    assert payload["read"] is False
    assert payload["created_at"]


@patch("app.services.notification_service.send_email_notification")
def test_notify_user_send_email(mock_send, db_session):
    user = UserFactory()
    notify_user(
        db_session,
        user_id=user.id,
        title="Email me",
        body="Details",
        send_email=True,
    )
    mock_send.assert_called_once()
