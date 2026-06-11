"""Coverage for llm_invoke and deep research pipeline."""

from unittest.mock import MagicMock, patch

import pytest

import pytest

from app.services.llm_invoke import invoke_generate, invoke_stream


def test_invoke_generate_success():
    provider = MagicMock()
    provider.name = "groq"
    provider.model_name = "test-model"
    provider.generate.return_value = "Hello world"
    provider.last_usage = {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8}

    with patch("app.services.llm_invoke._persist_metrics") as mock_persist:
        result = invoke_generate("Prompt", provider=provider, endpoint="test.generate")
    assert result == "Hello world"
    mock_persist.assert_called_once()


def test_invoke_generate_failure():
    provider = MagicMock()
    provider.name = "groq"
    provider.model_name = "test-model"
    provider.generate.side_effect = RuntimeError("provider down")

    with patch("app.services.llm_invoke._persist_metrics") as mock_persist:
        with pytest.raises(RuntimeError, match="provider down"):
            invoke_generate("Prompt", provider=provider)
    mock_persist.assert_called_once()


def test_invoke_stream_success():
    provider = MagicMock()
    provider.name = "groq"
    provider.model_name = "test-model"
    provider.stream_generate.return_value = iter(["Hel", "lo"])
    provider.last_usage = {"prompt_tokens": 2, "completion_tokens": 2, "total_tokens": 4}

    with patch("app.services.llm_invoke._persist_metrics") as mock_persist:
        tokens = list(invoke_stream("Prompt", provider=provider, endpoint="test.stream"))
    assert tokens == ["Hel", "lo"]
    mock_persist.assert_called_once()


def test_invoke_stream_failure():
    provider = MagicMock()
    provider.name = "groq"
    provider.model_name = "test-model"

    def _broken(_prompt, **_kwargs):
        yield "partial"
        raise RuntimeError("stream failed")

    provider.stream_generate.side_effect = _broken

    with patch("app.services.llm_invoke._persist_metrics") as mock_persist:
        with pytest.raises(RuntimeError, match="stream failed"):
            list(invoke_stream("Prompt", provider=provider))
    mock_persist.assert_called_once()


@patch("app.research.pipeline.generate_report")
@patch("app.research.pipeline.detect_contradictions")
@patch("app.research.pipeline.verify_sources")
@patch("app.research.pipeline.multi_hop_retrieval")
@patch("app.research.pipeline.plan_research")
def test_run_deep_research_success(
    mock_plan,
    mock_multi,
    mock_verify,
    mock_contra,
    mock_report,
    db_session,
):
    from app.research.pipeline import run_deep_research
    from app.schemas.agent_schemas import ResearchReportPayload
    from tests.factories import UserFactory

    user = UserFactory()
    mock_plan.return_value = {"goal": "Study topic", "search_queries": ["topic"]}
    mock_multi.return_value = (["chunk"], [], ["label"], [{"id": 1}], [{"step": 1}])
    mock_verify.return_value = {"confidence_score": 0.8}
    mock_contra.return_value = {"contradictions": []}
    mock_report.return_value = ResearchReportPayload(
        title="Deep Report",
        executive_summary="Summary",
        key_findings=["Finding"],
        detailed_analysis="Analysis",
        evidence_summary="Evidence",
        sources_reviewed=["S1"],
        references=[],
        open_questions=[],
        methodology="Hybrid",
        confidence_score=0.8,
        contradictions_noted=[],
        iterations=2,
    )

    result = run_deep_research(
        db_session,
        query="Explain topic",
        user_id=user.id,
        max_iterations=2,
    )
    assert result["report_id"]
    assert result["report"]["title"] == "Deep Report"


def test_list_research_reports(db_session):
    from app.models.research_report import ResearchReport
    from app.research.pipeline import list_research_reports
    from tests.factories import UserFactory

    user = UserFactory()
    db_session.add(
        ResearchReport(
            user_id=user.id,
            query="Topic",
            status="ready",
            report={"title": "Topic"},
        )
    )
    db_session.commit()
    rows = list_research_reports(db_session, user_id=user.id)
    assert len(rows) == 1


@patch("app.research.pipeline.plan_research", side_effect=RuntimeError("planner failed"))
def test_run_deep_research_failure(mock_plan, db_session):
    from app.research.pipeline import run_deep_research
    from app.models.research_report import ResearchReport
    from tests.factories import UserFactory

    user = UserFactory()
    with pytest.raises(RuntimeError, match="planner failed"):
        run_deep_research(db_session, query="Fail case", user_id=user.id)
    row = db_session.query(ResearchReport).filter(ResearchReport.user_id == user.id).first()
    assert row is not None
    assert row.status == "failed"
