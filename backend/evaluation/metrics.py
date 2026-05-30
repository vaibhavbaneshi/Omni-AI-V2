"""Evaluation metric calculators with RAGAS, DeepEval, and heuristic fallbacks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricScore:
    name: str
    score: float
    engine: str = "heuristic"


@dataclass
class CaseMetrics:
    case_id: str
    scores: list[MetricScore] = field(default_factory=list)
    engine: str = "heuristic"

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "engine": self.engine,
            "metrics": {item.name: round(item.score, 4) for item in self.scores},
        }


def _heuristic_metrics(
    *,
    question: str,
    answer: str,
    contexts: list[str],
    ground_truth: str,
) -> list[MetricScore]:
    answer_lower = answer.lower()
    truth_lower = ground_truth.lower()
    context_text = " ".join(contexts).lower()
    question_tokens = [token for token in question.lower().split() if len(token) > 2]

    truth_tokens = [token for token in truth_lower.split() if token][:6]
    faithfulness = (
        1.0
        if truth_tokens and all(token in context_text or token in answer_lower for token in truth_tokens[:3])
        else 0.55
        if any(token in context_text for token in truth_tokens)
        else 0.35
    )

    answer_relevancy = (
        1.0
        if question_tokens and sum(1 for token in question_tokens if token in answer_lower) >= min(2, len(question_tokens))
        else 0.45
    )

    context_precision = min(1.0, len(contexts) / 3) if contexts else 0.0
    context_recall = 1.0 if truth_lower in context_text or truth_lower in answer_lower else 0.35
    hallucination = max(0.0, 1.0 - faithfulness)
    response_quality = round(
        (faithfulness * 0.35)
        + (answer_relevancy * 0.25)
        + (context_precision * 0.15)
        + (context_recall * 0.15)
        + ((1.0 - hallucination) * 0.10),
        4,
    )

    return [
        MetricScore("faithfulness", faithfulness),
        MetricScore("answer_relevancy", answer_relevancy),
        MetricScore("context_precision", context_precision),
        MetricScore("context_recall", context_recall),
        MetricScore("hallucination", hallucination),
        MetricScore("response_quality", response_quality),
    ]


def _ragas_metrics(
    *,
    question: str,
    answer: str,
    contexts: list[str],
    ground_truth: str,
) -> list[MetricScore] | None:
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

    scores = [
        MetricScore("faithfulness", float(result["faithfulness"][0]), engine="ragas"),
        MetricScore("answer_relevancy", float(result["answer_relevancy"][0]), engine="ragas"),
        MetricScore("context_precision", float(result["context_precision"][0]), engine="ragas"),
        MetricScore("context_recall", float(result["context_recall"][0]), engine="ragas"),
    ]

    hallucination = max(0.0, 1.0 - scores[0].score)
    response_quality = round(
        sum(item.score for item in scores) / len(scores) * 0.9 + (1.0 - hallucination) * 0.1,
        4,
    )
    scores.extend(
        [
            MetricScore("hallucination", hallucination, engine="ragas"),
            MetricScore("response_quality", response_quality, engine="ragas"),
        ]
    )
    return scores


def _deepeval_metrics(
    *,
    question: str,
    answer: str,
    contexts: list[str],
    ground_truth: str,
) -> list[MetricScore] | None:
    """Optional DeepEval metrics — skipped when SDK or API keys are unavailable."""
    try:
        from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
        from deepeval.test_case import LLMTestCase
    except ImportError:
        return None

    test_case = LLMTestCase(
        input=question,
        actual_output=answer,
        expected_output=ground_truth,
        retrieval_context=contexts,
    )

    scores: list[MetricScore] = []
    try:
        faith_metric = FaithfulnessMetric(threshold=0.5)
        faith_metric.measure(test_case)
        scores.append(MetricScore("faithfulness", float(faith_metric.score or 0.0), engine="deepeval"))
    except Exception:
        return None

    try:
        relevancy_metric = AnswerRelevancyMetric(threshold=0.5)
        relevancy_metric.measure(test_case)
        scores.append(
            MetricScore("answer_relevancy", float(relevancy_metric.score or 0.0), engine="deepeval")
        )
    except Exception:
        pass

    if not scores:
        return None

    # DeepEval does not expose all four RAGAS metrics — fill gaps heuristically.
    heuristic = _heuristic_metrics(
        question=question,
        answer=answer,
        contexts=contexts,
        ground_truth=ground_truth,
    )
    existing = {item.name for item in scores}
    for item in heuristic:
        if item.name not in existing:
            scores.append(MetricScore(item.name, item.score, engine="deepeval-heuristic"))

    return scores


def score_rag_case(
    *,
    case_id: str,
    question: str,
    answer: str,
    contexts: list[str],
    ground_truth: str,
    engine_preference: str = "auto",
) -> CaseMetrics:
    """Score a single RAG case using the best available engine."""
    engines = []
    if engine_preference == "ragas":
        engines = [_ragas_metrics]
    elif engine_preference == "deepeval":
        engines = [_deepeval_metrics]
    elif engine_preference == "heuristic":
        engines = []
    else:
        engines = [_ragas_metrics, _deepeval_metrics]

    for calculator in engines:
        scores = calculator(
            question=question,
            answer=answer,
            contexts=contexts,
            ground_truth=ground_truth,
        )
        if scores:
            engine = scores[0].engine
            return CaseMetrics(case_id=case_id, scores=scores, engine=engine)

    scores = _heuristic_metrics(
        question=question,
        answer=answer,
        contexts=contexts,
        ground_truth=ground_truth,
    )
    return CaseMetrics(case_id=case_id, scores=scores, engine="heuristic")
