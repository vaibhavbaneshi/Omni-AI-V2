"""Orchestration evaluation for route/tool correctness."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.agent.orchestrator import AgentOrchestrator


def evaluate_orchestration(dataset_path: Path, output_dir: Path) -> Path:
    orchestrator = AgentOrchestrator()
    cases = json.loads(dataset_path.read_text(encoding="utf-8"))
    results = []

    for case in cases:
        route = orchestrator.plan(case["question"], mode="research")
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
                "route_precision": precision,
                "route_recall": recall,
                "correct": expected.issubset(actual),
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"orchestration_eval_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": str(dataset_path),
        "results": results,
        "accuracy": sum(1 for row in results if row["correct"]) / max(len(results), 1),
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Omni-AI orchestration evaluation")
    parser.add_argument("--dataset", default="eval/benchmark_dataset.json")
    parser.add_argument("--output", default="eval/reports")
    args = parser.parse_args()
    path = evaluate_orchestration(Path(args.dataset), Path(args.output))
    print(f"Orchestration evaluation report written to {path}")
