"""Integration tests — authentication and protected routes."""

from app.services.auth_service import create_access_token, create_refresh_token, hash_refresh_token, refresh_token_expires_at
from app.models.user_settings import UserSessionRecord
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


def test_refresh_token_rotates(client, db_session):
    user = UserFactory(username="refresh-user", email="refresh@example.com")
    token = create_refresh_token()
    db_session.add(
        UserSessionRecord(
            user_id=user.id,
            session_jti="old-jti",
            refresh_token_hash=hash_refresh_token(token),
            refresh_expires_at=refresh_token_expires_at(),
            device_label="pytest",
        )
    )
    db_session.commit()

    response = client.post("/auth/refresh", json={"refresh_token": token})

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["refresh_token"]
    assert payload["refresh_token"] != token


def test_logout_revokes_refresh_token(client, db_session):
    user = UserFactory(username="logout-user", email="logout@example.com")
    token = create_refresh_token()
    record = UserSessionRecord(
        user_id=user.id,
        session_jti="logout-jti",
        refresh_token_hash=hash_refresh_token(token),
        refresh_expires_at=refresh_token_expires_at(),
        device_label="pytest",
    )
    db_session.add(record)
    db_session.commit()

    response = client.post("/auth/logout", json={"refresh_token": token})

    assert response.status_code == 200
    db_session.refresh(record)
    assert record.revoked_at is not None
