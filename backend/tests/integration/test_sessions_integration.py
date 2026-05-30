"""Integration tests — chat session CRUD."""

from unittest.mock import patch

from tests.factories import ChatSessionFactory, MessageFactory


@patch("app.api.session_routes.generate_chat_title", return_value="Billing Question")
def test_create_session(_mock_title, auth_client):
    response = auth_client.post(
        "/sessions?title=New+Chat&first_message=What+is+the+refund+policy",
        headers=auth_client.auth_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Billing Question"
    assert "id" in payload


def test_list_sessions(auth_client, db_session):
    ChatSessionFactory(user=auth_client.auth_user, title="Alpha")
    ChatSessionFactory(user=auth_client.auth_user, title="Beta")

    response = auth_client.get("/sessions", headers=auth_client.auth_headers)
    assert response.status_code == 200
    titles = {row["title"] for row in response.json()}
    assert "Alpha" in titles
    assert "Beta" in titles


def test_get_session_messages(auth_client, db_session):
    session = ChatSessionFactory(user=auth_client.auth_user, title="Messages Chat")
    MessageFactory(session=session, role="user", content="Hello")
    MessageFactory(session=session, role="assistant", content="Hi there")

    response = auth_client.get(
        f"/sessions/{session.id}/messages",
        headers=auth_client.auth_headers,
    )
    assert response.status_code == 200
    messages = response.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_update_session_title(auth_client, db_session):
    session = ChatSessionFactory(user=auth_client.auth_user, title="Old Title")

    response = auth_client.patch(
        f"/sessions/{session.id}?title=Renamed+Chat",
        headers=auth_client.auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Renamed Chat"


def test_delete_session(auth_client, db_session):
    session = ChatSessionFactory(user=auth_client.auth_user, title="Delete Me")
    MessageFactory(session=session, role="user", content="temp")

    response = auth_client.delete(
        f"/sessions/{session.id}",
        headers=auth_client.auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["session_id"] == session.id

    messages = auth_client.get(
        f"/sessions/{session.id}/messages",
        headers=auth_client.auth_headers,
    )
    assert messages.json() == []
