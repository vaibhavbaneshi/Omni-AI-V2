"""Evaluation runner for RAG quality and orchestration routing."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evaluation.exporters import write_csv_report, write_json_report
from evaluation.metrics import score_rag_case


def _default_dataset_path() -> Path:
    return Path(__file__).resolve().parent / "datasets" / "sample_rag_eval.json"


def _default_output_dir() -> Path:
    # Repo-root eval/reports keeps compatibility with existing CI smoke job.
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "eval" / "reports"


def _aggregate_metric(results: list[dict[str, Any]], metric_name: str) -> float:
    values = [
        float(row["metrics"][metric_name])
        for row in results
        if metric_name in row.get("metrics", {})
    ]
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)


def evaluate_orchestration_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from app.agent.orchestrator import AgentOrchestrator

    orchestrator = AgentOrchestrator()
    results: list[dict[str, Any]] = []

    for case in cases:
        if not case.get("expected_tools"):
            continue

        route = orchestrator.plan(case["question"], mode=case.get("mode", "research"))
        expected = set(case.get("expected_tools", []))
        actual = set(route.tools)
        precision = len(expected.intersection(actual)) / len(actual) if actual else 0.0
        recall = len(expected.intersection(actual)) / len(expected) if expected else 1.0

        results.append(
            {
                "id": case["id"],
                "strategy": route.strategy,
                "tools": route.tools,
                "expected_tools": list(expected),
                "route_precision": round(precision, 4),
                "route_recall": round(recall, 4),
                "correct": expected.issubset(actual),
            }
        )

    return results


def _resolve_answer(case: dict[str, Any], *, generate_answers: bool) -> str:
    if generate_answers:
        try:
            from app.services.rag_service import chat_with_rag

            result = chat_with_rag(case["question"])
            return str(result.get("response") or "")
        except Exception:
            pass

    return str(case.get("sample_answer") or case.get("ground_truth") or "")


def run_evaluation(
    *,
    dataset_path: Path | None = None,
    output_dir: Path | None = None,
    run_rag: bool = True,
    run_orchestration: bool = True,
    generate_answers: bool = False,
    engine_preference: str = "auto",
) -> dict[str, Any]:
    """Run RAG and orchestration evaluation and write JSON + CSV reports."""
    dataset = dataset_path or _default_dataset_path()
    output = output_dir or _default_output_dir()
    cases = json.loads(dataset.read_text(encoding="utf-8"))

    rag_results: list[dict[str, Any]] = []
    if run_rag:
        for case in cases:
            if case.get("type") == "orchestration-only":
                continue

            answer = _resolve_answer(case, generate_answers=generate_answers)
            scored = score_rag_case(
                case_id=case["id"],
                question=case["question"],
                answer=answer,
                contexts=case.get("contexts", []),
                ground_truth=case.get("ground_truth", ""),
                engine_preference=engine_preference,
            )
            rag_results.append(scored.as_dict())

    orchestration_results: list[dict[str, Any]] = []
    if run_orchestration:
        orchestration_results = evaluate_orchestration_cases(cases)

    summary: dict[str, Any] = {
        "cases_evaluated": len(rag_results),
        "orchestration_cases": len(orchestration_results),
    }

    if rag_results:
        summary["avg_faithfulness"] = _aggregate_metric(rag_results, "faithfulness")
        summary["avg_answer_relevancy"] = _aggregate_metric(rag_results, "answer_relevancy")
        summary["avg_context_precision"] = _aggregate_metric(rag_results, "context_precision")
        summary["avg_context_recall"] = _aggregate_metric(rag_results, "context_recall")
        summary["avg_hallucination"] = _aggregate_metric(rag_results, "hallucination")
        summary["avg_response_quality"] = _aggregate_metric(rag_results, "response_quality")

    if orchestration_results:
        summary["orchestration_accuracy"] = round(
            sum(1 for row in orchestration_results if row.get("correct")) / max(len(orchestration_results), 1),
            4,
        )

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": str(dataset),
        "engine_preference": engine_preference,
        "generate_answers": generate_answers,
        "summary": summary,
        "rag_results": rag_results,
        "orchestration_results": orchestration_results,
    }

    json_path = write_json_report(report, output)
    csv_path = write_csv_report(report, output)

    report["report_paths"] = {
        "json": str(json_path),
        "csv": str(csv_path),
    }
    return report
