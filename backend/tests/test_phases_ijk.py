"""Tests for multi-agent platform and RBAC (Phases J/K)."""

from unittest.mock import patch

from app.core.rbac import get_user_role, user_has_min_role
from app.models.rbac import ROLE_ADMIN, UserRole
from tests.factories import UserFactory


@patch("app.core.rbac.user_has_admin_access", return_value=False)
def test_rbac_defaults_to_viewer(_mock_admin, db_session):
    user = UserFactory()
    assert get_user_role(db_session, user) == "viewer"


@patch("app.core.rbac.user_has_admin_access", return_value=False)
@patch("app.core.rbac.get_settings")
def test_rbac_role_assignment(mock_settings, _mock_admin, db_session):
    mock_settings.return_value.ENABLE_RBAC = True
    user = UserFactory()
    db_session.add(UserRole(user_id=user.id, role=ROLE_ADMIN))
    db_session.commit()
    assert get_user_role(db_session, user) == ROLE_ADMIN
    assert user_has_min_role(db_session, user, "manager") is True
    assert user_has_min_role(db_session, user, ROLE_ADMIN) is True

    viewer = UserFactory()
    assert user_has_min_role(db_session, viewer, ROLE_ADMIN) is False


@patch("app.agent.multi_agent_platform.invoke_generate")
@patch("app.agent.multi_agent_platform.AgentOrchestrator")
def test_multi_agent_platform_persists_trace(mock_orchestrator, mock_invoke, db_session):
    from app.agent.multi_agent_platform import run_multi_agent_platform
    from app.agent.schemas import AgentRoute, ContextBundle
    from app.models.agent_trace import AgentTrace

    mock_invoke.side_effect = [
        '{"goal": "test", "subtasks": [{"agent": "research", "task": "Find facts"}]}',
        '{"approved": true, "gaps": [], "confidence": "high", "notes": "ok"}',
        "Final synthesized answer.",
    ]

    bundle = ContextBundle(
        context="Evidence from research.",
        sources=[],
        tool_results=[],
        route=AgentRoute(
            strategy="research-hybrid",
            tools=["retrieval"],
            reason="test",
            confidence=0.8,
            mode="research",
        ),
        traces=[],
    )
    mock_orchestrator.return_value.run.return_value = bundle

    user = UserFactory()
    result = run_multi_agent_platform(
        db_session,
        query="Summarize market trends",
        user_id=user.id,
    )

    assert result["agent"] == "multi-agent-platform"
    assert result["trace_id"]
    trace = db_session.query(AgentTrace).filter(AgentTrace.id == result["trace_id"]).first()
    assert trace is not None
    assert trace.status == "complete"
    assert trace.planner_output is not None
    assert trace.agent_steps
