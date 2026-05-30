"""RAG evaluation pipeline (backward-compatible CLI wrapper)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from evaluation.runner import run_evaluation  # noqa: E402


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Omni-AI RAG evaluation")
    parser.add_argument("--dataset", default="eval/benchmark_dataset.json")
    parser.add_argument("--output", default="eval/reports")
    parser.add_argument("--engine", default="auto")
    args = parser.parse_args()

    report = run_evaluation(
        dataset_path=Path(args.dataset),
        output_dir=Path(args.output),
        run_rag=True,
        run_orchestration=False,
        engine_preference=args.engine,
    )
    print(f"RAG evaluation report written to {report['report_paths']['json']}")
