"""Integration tests — authentication and protected routes."""

from app.services.auth_service import create_access_token
from tests.factories import UserFactory


def test_users_me_requires_auth(client):
    response = client.get("/users/me")
    assert response.status_code == 401


def test_users_me_returns_profile(auth_client):
    response = auth_client.get("/users/me", headers=auth_client.auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["username"] == auth_client.auth_user.username
    assert payload["email"] == auth_client.auth_user.email


def test_invalid_token_rejected(client, db_session):
    UserFactory(username="valid-user", email="valid@example.com")
    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401


def test_valid_token_for_existing_user(client, db_session):
    user = UserFactory(username="token-user", email="token@example.com")
    token = create_access_token({"sub": user.username})
    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["id"] == user.id
