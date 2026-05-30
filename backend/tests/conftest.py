"""Shared pytest fixtures: in-memory SQLite DB, auth client, factories."""

from __future__ import annotations

import os
from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Set test env before app imports.
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-with-32-characters-min")
os.environ.setdefault("LLM_PROVIDER", "groq")
os.environ.setdefault("GROQ_API_KEY", "test-key")
os.environ.setdefault("ENABLE_USAGE_TRACKING", "false")

from app.db.database import Base
from app.db.session import get_db
from app.models import analytics  # noqa: F401 — register analytics tables
from app.models.chat_session import ChatSession
from app.models.conversation_summary import ConversationSummary
from app.models.document import DocumentCollection, DocumentRecord
from app.models.memory import UserMemory
from app.models.message import Message
from app.models.user import User
from app.services.auth_service import create_access_token
from tests.factories import UserFactory, bind_factories


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    connection = db_engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = TestingSessionLocal()
    bind_factories(session)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def auth_context(db_session):
    user = UserFactory()
    token = create_access_token({"sub": user.username})
    headers = {"Authorization": f"Bearer {token}"}
    return {"user": user, "token": token, "headers": headers}


@pytest.fixture
def client(db_session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    with patch("app.core.health.run_startup_checks", return_value={"status": "started"}):
        with patch("app.db.migrations.run_migrations"):
            from app.main import app

            app.dependency_overrides[get_db] = override_get_db
            with TestClient(app) as test_client:
                yield test_client
            app.dependency_overrides.clear()


@pytest.fixture
def auth_client(client, auth_context):
    """TestClient with Authorization header and user/session helpers."""
    client.auth_user = auth_context["user"]
    client.auth_headers = auth_context["headers"]
    return client
