from datetime import datetime, timedelta

from jose import jwt

from app.services.auth_service import create_access_token, get_jwt_secret, get_jwt_algorithm


def test_create_access_token_roundtrip():
    token = create_access_token({"sub": "test-user"})
    payload = jwt.decode(token, get_jwt_secret(), algorithms=[get_jwt_algorithm()])
    assert payload["sub"] == "test-user"


def test_expired_token_rejected(client):
    token = jwt.encode(
        {"sub": "expired-user", "exp": datetime.utcnow() - timedelta(minutes=1)},
        get_jwt_secret(),
        algorithm=get_jwt_algorithm(),
    )

    response = client.get("/sessions", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"
