"""Evaluation framework tests (heuristic engine — no RAGAS/DeepEval required in CI)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.api.evaluation_routes import EvaluationRunRequest, require_evaluation_admin
from app.models.user import User
from evaluation.metrics import score_rag_case
from evaluation.runner import run_evaluation


def test_score_rag_case_heuristic():
    scored = score_rag_case(
        case_id="test-1",
        question="What is the refund policy?",
        answer="Annual subscriptions can be refunded within 14 days.",
        contexts=["Annual subscriptions can be refunded within 14 days of purchase."],
        ground_truth="Annual subscriptions can be refunded within 14 days.",
        engine_preference="heuristic",
    )

    metrics = scored.as_dict()["metrics"]
    assert scored.engine == "heuristic"
    assert metrics["faithfulness"] >= 0.5
    assert metrics["answer_relevancy"] >= 0.4
    assert "hallucination" in metrics
    assert "response_quality" in metrics


def test_run_evaluation_writes_json_and_csv(tmp_path: Path):
    dataset = tmp_path / "cases.json"
    dataset.write_text(
        json.dumps(
            [
                {
                    "id": "case-1",
                    "question": "What is MFA?",
                    "ground_truth": "MFA requires a second factor.",
                    "contexts": ["MFA requires a second factor during login."],
                    "sample_answer": "MFA requires a second factor during login.",
                }
            ]
        ),
        encoding="utf-8",
    )

    report = run_evaluation(
        dataset_path=dataset,
        output_dir=tmp_path / "reports",
        run_rag=True,
        run_orchestration=False,
        engine_preference="heuristic",
    )

    assert report["summary"]["cases_evaluated"] == 1
    assert Path(report["report_paths"]["json"]).exists()
    assert Path(report["report_paths"]["csv"]).exists()


def test_evaluation_admin_gate_blocks_production(monkeypatch):
    user = User(id=1, username="tester", email="user@example.com", password="hashed")

    class _Settings:
        ENVIRONMENT = "production"
        EVAL_ADMIN_EMAILS = "admin@example.com"
        ANALYTICS_ADMIN_EMAILS = ""

    monkeypatch.setattr("app.core.admin_access.get_settings", lambda: _Settings())

    with pytest.raises(HTTPException) as exc:
        require_evaluation_admin(user)

    assert exc.value.status_code == 403


def test_evaluation_admin_gate_allows_listed_email(monkeypatch):
    user = User(id=1, username="admin", email="admin@example.com", password="hashed")

    class _Settings:
        ENVIRONMENT = "production"
        EVAL_ADMIN_EMAILS = "admin@example.com"
        ANALYTICS_ADMIN_EMAILS = ""

    monkeypatch.setattr("app.core.admin_access.get_settings", lambda: _Settings())

    assert require_evaluation_admin(user).email == "admin@example.com"


def test_evaluation_run_request_defaults():
    payload = EvaluationRunRequest()
    assert payload.run_rag is True
    assert payload.generate_answers is False
