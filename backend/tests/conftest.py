import os
from unittest.mock import patch

import pytest

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-with-32-characters-min")


@pytest.fixture
def client():
    with patch("app.core.health.check_ollama", return_value={"status": "ok"}):
        with patch("app.core.health.check_chroma", return_value={"status": "ok"}):
            with patch("app.core.health.check_database", return_value={"status": "ok"}):
                from fastapi.testclient import TestClient
                from app.main import app

                with TestClient(app) as test_client:
                    yield test_client
