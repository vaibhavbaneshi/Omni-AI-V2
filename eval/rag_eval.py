"""RAG evaluation pipeline (RAGAS + heuristic fallback)."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class RagEvalResult:
    metric: str
    score: float


def _heuristic_scores(question: str, answer: str, contexts: list[str], ground_truth: str) -> list[RagEvalResult]:
    answer_lower = answer.lower()
    truth_lower = ground_truth.lower()
    context_text = " ".join(contexts).lower()

    faithfulness = 1.0 if any(token in context_text for token in truth_lower.split()[:3]) else 0.5
    answer_relevancy = 1.0 if any(token in answer_lower for token in question.lower().split()[:4]) else 0.4
    context_precision = min(1.0, len(contexts) / 3) if contexts else 0.0
    context_recall = 1.0 if truth_lower in context_text or truth_lower in answer_lower else 0.3
    hallucination = 0.0 if faithfulness > 0.6 else 0.7

    return [
        RagEvalResult("faithfulness", faithfulness),
        RagEvalResult("answer_relevancy", answer_relevancy),
        RagEvalResult("context_precision", context_precision),
        RagEvalResult("context_recall", context_recall),
        RagEvalResult("hallucination", hallucination),
    ]


def _ragas_scores(question: str, answer: str, contexts: list[str], ground_truth: str) -> list[RagEvalResult] | None:
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )
    except ImportError:
        return None

    dataset = Dataset.from_dict(
        {
            "question": [question],
            "answer": [answer],
            "contexts": [contexts],
            "ground_truth": [ground_truth],
        }
    )
    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    )
    scores = []
    for metric_name in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        value = float(result[metric_name][0])
        scores.append(RagEvalResult(metric_name, value))
    return scores


def evaluate_case(case: dict[str, Any], answer: str) -> dict[str, Any]:
    question = case["question"]
    contexts = case.get("contexts", [])
    ground_truth = case.get("ground_truth", "")
    scores = _ragas_scores(question, answer, contexts, ground_truth)
    engine = "ragas"
    if scores is None:
        scores = _heuristic_scores(question, answer, contexts, ground_truth)
        engine = "heuristic"
    return {
        "id": case["id"],
        "engine": engine,
        "metrics": {item.metric: item.score for item in scores},
    }


def run(dataset_path: Path, output_dir: Path) -> Path:
    cases = json.loads(dataset_path.read_text(encoding="utf-8"))
    results = []
    for case in cases:
        answer = case.get("sample_answer") or case.get("ground_truth", "")
        results.append(evaluate_case(case, answer))

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"rag_eval_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": str(dataset_path),
        "results": results,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Omni-AI RAG evaluation")
    parser.add_argument("--dataset", default="eval/benchmark_dataset.json")
    parser.add_argument("--output", default="eval/reports")
    args = parser.parse_args()
    path = run(Path(args.dataset), Path(args.output))
    print(f"RAG evaluation report written to {path}")
