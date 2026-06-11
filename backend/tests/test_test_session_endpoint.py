"""Tests for TEST_MODE auth helper endpoint."""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_mode_client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    with patch.dict(os.environ, {"TEST_MODE": "true"}):
        with patch("app.core.health.run_startup_checks", return_value={"status": "started"}):
            with patch("app.db.migrations.run_migrations"):
                from app.db.session import get_db
                from app.main import app

                app.dependency_overrides[get_db] = override_get_db
                # Re-import router registration by creating fresh app is hard;
                # call route function directly instead via TestClient after including router.
                from app.api.test_utils_routes import router as test_router

                if not any(getattr(route, "path", "") == "/auth/test-session" for route in app.routes):
                    app.include_router(test_router)
                with TestClient(app) as client:
                    yield client
                app.dependency_overrides.clear()


def test_test_session_disabled_without_test_mode(client):
    response = client.post("/auth/test-session")
    assert response.status_code == 404


def test_test_session_creates_user(test_mode_client):
    response = test_mode_client.post("/auth/test-session")
    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == "test@omni.local"
    assert payload["access_token"]
