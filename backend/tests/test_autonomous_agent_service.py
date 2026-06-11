"""Tests for autonomous agent scheduling."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.agents.lifecycle import create_agent
from app.jobs.agent_jobs import poll_due_agents
from tests.factories import UserFactory


@patch("app.jobs.agent_jobs.SessionLocal")
@patch("app.services.agent_scheduler_service.enqueue_agent_run_now")
def test_poll_due_agents_picks_up_due_agents(mock_enqueue, mock_session_local, db_session):
    user = UserFactory()
    due = create_agent(
        db_session,
        user_id=user.id,
        name="Due agent",
        agent_type="document_monitor",
        schedule_kind="hourly",
    )
    due.next_run_at = datetime.utcnow() - timedelta(minutes=5)
    db_session.commit()

    future = create_agent(
        db_session,
        user_id=user.id,
        name="Future agent",
        agent_type="document_monitor",
        schedule_kind="hourly",
    )
    future.next_run_at = datetime.utcnow() + timedelta(hours=2)
    db_session.commit()

    mock_session_local.return_value = db_session
    mock_enqueue.return_value = "job-123"
    count = poll_due_agents()

    assert count == 1
    mock_enqueue.assert_called_once_with(due.id)


@patch("app.jobs.agent_jobs.SessionLocal")
@patch("app.services.agent_scheduler_service.enqueue_agent_run_now", return_value=None)
@patch("app.agents.executor.execute_agent")
def test_poll_due_agents_inline_when_queue_unavailable(mock_execute, mock_enqueue, mock_session_local, db_session):
    user = UserFactory()
    agent = create_agent(
        db_session,
        user_id=user.id,
        name="Inline agent",
        agent_type="document_monitor",
        schedule_kind="hourly",
    )
    agent.next_run_at = datetime.utcnow() - timedelta(minutes=1)
    db_session.commit()

    mock_session_local.return_value = db_session
    mock_execute.return_value = MagicMock(id=1, status="complete")
    count = poll_due_agents()

    assert count == 1
    mock_execute.assert_called_once()
