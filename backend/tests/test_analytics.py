"""Analytics API and aggregation tests."""

from datetime import datetime, timedelta

from app.models.analytics import ApiUsage, ModelUsage, TokenUsage
from app.services.analytics_service import get_platform_overview, get_user_overview
from tests.factories import ChatSessionFactory, UserFactory


def _seed_usage(db_session, user_id: int):
    now = datetime.utcnow()
    db_session.add(
        ApiUsage(
            user_id=user_id,
            method="POST",
            path="/chat-stream",
            status_code=200,
            duration_ms=120.5,
            created_at=now,
        )
    )
    model_row = ModelUsage(
        user_id=user_id,
        provider="groq",
        model="llama-3.3-70b-versatile",
        endpoint="rag.stream",
        latency_ms=800.0,
        success=True,
        created_at=now,
    )
    db_session.add(model_row)
    db_session.flush()
    db_session.add(
        TokenUsage(
            user_id=user_id,
            model_usage_id=model_row.id,
            provider="groq",
            model="llama-3.3-70b-versatile",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            prompt_chars=400,
            completion_chars=200,
            created_at=now,
        )
    )
    db_session.commit()


def test_get_user_overview(db_session):
    user = UserFactory()
    ChatSessionFactory(user_id=user.id, title="Analytics Chat")
    _seed_usage(db_session, user.id)

    overview = get_user_overview(db_session, user_id=user.id, days=30)
    assert overview["scope"] == "user"
    assert overview["ai"]["total_tokens"] >= 150
    assert overview["users"]["sessions"] >= 1
    assert overview["ai"]["avg_latency_ms"] > 0


def test_get_platform_overview(db_session):
    user = UserFactory()
    _seed_usage(db_session, user.id)

    overview = get_platform_overview(db_session, days=30)
    assert overview["scope"] == "platform"
    assert overview["users"]["total_users"] >= 1
    assert overview["ai"]["total_tokens"] >= 150


def test_analytics_overview_endpoint(auth_client, db_session):
    _seed_usage(db_session, auth_client.auth_user.id)

    response = auth_client.get("/analytics/overview?days=30", headers=auth_client.auth_headers)
    assert response.status_code == 200
    assert response.json()["scope"] == "user"


def test_platform_analytics_dev_mode(auth_client, db_session):
    response = auth_client.get("/analytics/platform?days=7", headers=auth_client.auth_headers)
    assert response.status_code == 200
    assert response.json()["scope"] == "platform"
