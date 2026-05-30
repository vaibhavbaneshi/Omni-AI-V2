"""Export evaluation reports to JSON and CSV."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_json_report(report: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"evaluation_{timestamp}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path


def write_csv_report(report: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"evaluation_{timestamp}.csv"

    metric_names = [
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
        "hallucination",
        "response_quality",
    ]

    rows: list[dict[str, Any]] = []

    for result in report.get("rag_results", []):
        row = {
            "section": "rag",
            "case_id": result.get("case_id") or result.get("id"),
            "engine": result.get("engine", ""),
        }
        metrics = result.get("metrics", {})
        for name in metric_names:
            row[name] = metrics.get(name, "")
        rows.append(row)

    for result in report.get("orchestration_results", []):
        rows.append(
            {
                "section": "orchestration",
                "case_id": result.get("id"),
                "engine": "orchestrator",
                "faithfulness": "",
                "answer_relevancy": "",
                "context_precision": "",
                "context_recall": "",
                "hallucination": "",
                "response_quality": result.get("route_precision", ""),
                "route_recall": result.get("route_recall", ""),
                "correct": result.get("correct", ""),
            }
        )

    if not rows:
        path.write_text("section,case_id,engine\n", encoding="utf-8")
        return path

    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    return path
