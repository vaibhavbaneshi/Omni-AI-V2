import os
from unittest.mock import patch

import pytest

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-with-32-characters-min")
os.environ.setdefault("LLM_PROVIDER", "groq")
os.environ.setdefault("GROQ_API_KEY", "test-key")


@pytest.fixture
def client():
    with patch("app.core.health.run_startup_checks", return_value={"status": "started"}):
        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app) as test_client:
            yield test_client
