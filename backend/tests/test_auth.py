from jose import jwt

from app.services.auth_service import create_access_token, get_jwt_secret, get_jwt_algorithm


def test_create_access_token_roundtrip():
    token = create_access_token({"sub": "test-user"})
    payload = jwt.decode(token, get_jwt_secret(), algorithms=[get_jwt_algorithm()])
    assert payload["sub"] == "test-user"
