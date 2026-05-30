"""Integration tests — workspace settings endpoints."""

from app.services.auth_service import verify_password


def test_get_settings(auth_client):
    response = auth_client.get("/settings", headers=auth_client.auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert "profile" in payload
    assert "security" in payload
    assert "preferences" in payload
    assert "api" in payload
    assert "billing" in payload
    assert payload["profile"]["email"] == auth_client.auth_user.email


def test_update_profile(auth_client):
    response = auth_client.patch(
        "/settings/profile",
        headers=auth_client.auth_headers,
        json={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": auth_client.auth_user.email,
            "bio": "Analytical engine operator",
        },
    )
    assert response.status_code == 200
    assert response.json()["first_name"] == "Ada"
    assert response.json()["bio"] == "Analytical engine operator"


def test_change_password(auth_client, db_session):
    response = auth_client.post(
        "/settings/password",
        headers=auth_client.auth_headers,
        json={
            "current_password": "test-password",
            "new_password": "new-test-password",
            "confirm_password": "new-test-password",
        },
    )
    assert response.status_code == 200
    db_session.refresh(auth_client.auth_user)
    assert verify_password("new-test-password", auth_client.auth_user.password)


def test_two_factor_setup_and_enable(auth_client):
    setup = auth_client.get("/settings/2fa/setup", headers=auth_client.auth_headers)
    assert setup.status_code == 200
    secret = setup.json()["secret"]

    import pyotp

    code = pyotp.TOTP(secret).now()
    enabled = auth_client.post(
        "/settings/2fa/enable",
        headers=auth_client.auth_headers,
        json={"code": code},
    )
    assert enabled.status_code == 200
    assert enabled.json()["totp_enabled"] is True


def test_regenerate_api_key(auth_client):
    response = auth_client.post(
        "/settings/api-key/regenerate",
        headers=auth_client.auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["api_key"].startswith("omni_")


def test_billing_plan_change(auth_client):
    response = auth_client.post(
        "/settings/billing/plan",
        headers=auth_client.auth_headers,
        json={"plan": "pro"},
    )
    assert response.status_code == 200
    assert response.json()["plan"] == "pro"
    assert response.json()["amount_cents"] == 2000
