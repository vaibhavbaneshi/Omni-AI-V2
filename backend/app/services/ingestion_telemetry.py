"""Structured ingestion logging, timing, and timeout detection."""

from __future__ import annotations

import logging
import resource
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("omniai.ingestion")


def _rss_mb() -> float | None:
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # macOS reports bytes; Linux reports kilobytes.
        value = usage.ru_maxrss
        if value > 10_000_000:
            return round(value / (1024 * 1024), 1)
        return round(value / 1024, 1)
    except Exception:
        return None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class IngestionContext:
    document_id: int
    filename: str
    user_id: int
    session_id: int | None = None
    started_at: float = field(default_factory=time.perf_counter)
    stage_started_at: float = field(default_factory=time.perf_counter)
    current_stage: str = "queued"

    def log(self, event: str, level: int = logging.INFO, **fields: Any) -> None:
        elapsed_ms = round((time.perf_counter() - self.started_at) * 1000, 1)
        stage_ms = round((time.perf_counter() - self.stage_started_at) * 1000, 1)
        memory_mb = _rss_mb()
        payload = {
            "event": event,
            "document_id": self.document_id,
            "filename": self.filename,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "stage": self.current_stage,
            "elapsed_ms": elapsed_ms,
            "stage_ms": stage_ms,
            "memory_mb": memory_mb,
            **fields,
        }
        parts = [f"[{event}]", f"document_id={self.document_id}", f"stage={self.current_stage}"]
        for key, value in fields.items():
            parts.append(f"{key}={value}")
        parts.append(f"elapsed_ms={elapsed_ms}")
        if memory_mb is not None:
            parts.append(f"memory_mb={memory_mb}")
        logger.log(level, " ".join(str(part) for part in parts), extra={"ingestion": payload})

    def warn_if_slow(self, threshold_seconds: float, label: str) -> None:
        elapsed = time.perf_counter() - self.stage_started_at
        if elapsed >= threshold_seconds:
            self.log(
                "SLOW_STAGE",
                level=logging.WARNING,
                label=label,
                threshold_seconds=threshold_seconds,
                elapsed_seconds=round(elapsed, 1),
            )

    @contextmanager
    def stage(self, name: str, slow_after_seconds: float | None = None):
        previous = self.current_stage
        self.current_stage = name
        self.stage_started_at = time.perf_counter()
        self.log(f"{name.upper()}_START")
        try:
            yield self
            if slow_after_seconds is not None:
                self.warn_if_slow(slow_after_seconds, name)
            self.log(
                f"{name.upper()}_COMPLETE",
                stage_duration_ms=round((time.perf_counter() - self.stage_started_at) * 1000, 1),
            )
        except Exception as exc:
            logger.exception(
                "[ERROR] document_id=%s stage=%s error=%s",
                self.document_id,
                self.current_stage,
                exc,
            )
            raise
        finally:
            self.current_stage = previous
            self.stage_started_at = time.perf_counter()


STAGE_LABELS = {
    "queued": "Queued for indexing...",
    "loading": "Loading document...",
    "chunking": "Chunking text...",
    "embedding": "Generating embeddings...",
    "vector_store": "Storing vectors...",
    "finalizing": "Finalizing...",
    "ready": "Ready",
    "failed": "Failed",
}
