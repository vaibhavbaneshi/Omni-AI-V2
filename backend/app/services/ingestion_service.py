"""Background document ingestion worker with stage tracking and structured logs."""

from __future__ import annotations

import logging
import os
import time

from app.db.session import SessionLocal
from app.models.document import DocumentRecord
from app.services.documents_services import process_document
from app.services.indexing_progress import mark_indexing_failed, mark_indexing_ready, update_indexing_progress
from app.services.ingestion_telemetry import IngestionContext
from app.services.usage_tracking_service import record_ingestion_event

logger = logging.getLogger(__name__)

MAX_INDEXING_SECONDS = 900  # 15 minutes — matches frontend stale detection
QUEUED_STALE_SECONDS = 45  # no progress from queued → likely background task never ran


def run_ingest_document_record(document_id: int, job_id: str | None = None) -> None:
    """Entry point for BackgroundTasks or direct sync invoke."""
    task_logger = logging.getLogger("omniai.ingestion")
    task_logger.info(
        "[INGEST_TASK_START] job_id=%s document_id=%s pid=%s embedding_provider=%s",
        job_id,
        document_id,
        os.getpid(),
        __import__("app.core.app_settings", fromlist=["get_settings"]).get_settings().EMBEDDING_PROVIDER,
    )
    try:
        ingest_document_record(document_id, job_id=job_id)
        task_logger.info("[INGEST_TASK_COMPLETE] job_id=%s document_id=%s", job_id, document_id)
    except Exception:
        task_logger.exception(
            "[INGEST_TASK_CRASHED] job_id=%s document_id=%s — see traceback above",
            job_id,
            document_id,
        )
        raise


def ingest_document_record(
    document_id: int,
    job_id: str | None = None,
    *,
    propagate_errors: bool = False,
) -> None:
    db = SessionLocal()
    started = time.perf_counter()
    document = None
    ctx: IngestionContext | None = None

    try:
        document = (
            db.query(DocumentRecord)
            .filter(DocumentRecord.id == document_id)
            .first()
        )
        if not document:
            logger.warning("[INGEST_SKIP] document_id=%s reason=missing_record", document_id)
            return

        if not document.storage_path or not os.path.exists(document.storage_path):
            raise FileNotFoundError("Uploaded file is no longer available on disk.")

        ctx = IngestionContext(
            document_id=document.id,
            filename=document.filename,
            user_id=document.user_id,
            session_id=document.session_id,
        )
        ctx.log(
            "UPLOAD_COMPLETE",
            size=document.file_size,
            path=document.storage_path,
            job_id=job_id or document.indexing_job_id,
        )

        update_indexing_progress(
            db,
            document.id,
            stage="loading",
            mark_started=True,
        )

        chunk_count = process_document(
            file_path=document.storage_path,
            filename=document.filename,
            user_id=document.user_id,
            workspace_id=document.workspace_id,
            collection_id=document.collection_id,
            session_id=document.session_id,
            document_id=document.id,
            db=db,
            telemetry=ctx,
        )

        with ctx.stage("finalizing", slow_after_seconds=30):
            mark_indexing_ready(db, document.id, chunk_count)
            db.refresh(document)

        record_ingestion_event(
            user_id=document.user_id,
            filename=document.filename,
            chunks_created=chunk_count,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            success=True,
        )
        ctx.log("INDEXING_COMPLETE", chunk_count=chunk_count)

        from app.services.document_intelligence_service import schedule_document_insights_generation

        schedule_document_insights_generation(document.id)
    except Exception as exc:
        db.rollback()
        filename = document.filename if document else f"document:{document_id}"
        user_id = document.user_id if document else 0
        record_ingestion_event(
            user_id=user_id,
            filename=filename,
            chunks_created=0,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            success=False,
            error_message=str(exc),
        )
        if ctx:
            ctx.log("ERROR", level=logging.ERROR, error=str(exc), error_type=type(exc).__name__)
        else:
            logger.exception("[ERROR] document_id=%s stage=startup error=%s", document_id, exc)

        if document:
            try:
                if not propagate_errors:
                    mark_indexing_failed(db, document.id, str(exc))
            except Exception:
                db.rollback()
                logger.exception(
                    "Failed to persist indexing failure document_id=%s",
                    document.id,
                )
        if propagate_errors:
            raise
    finally:
        if document and document.storage_path and os.path.exists(document.storage_path):
            if document.indexing_stage == "ready":
                try:
                    os.remove(document.storage_path)
                    parent = os.path.dirname(document.storage_path)
                    try:
                        os.rmdir(parent)
                    except OSError:
                        pass
                    if ctx:
                        ctx.log("TEMP_FILE_CLEANED", path=document.storage_path)
                except Exception:
                    logger.exception(
                        "Failed to clean temporary upload file document_id=%s path=%s",
                        document.id,
                        document.storage_path,
                    )
        db.close()


def detect_stale_indexing(document: DocumentRecord) -> str | None:
    if document.chunks_created > 0 or document.indexing_stage == "ready":
        return None
    if document.indexing_stage == "failed":
        return document.indexing_error

    from datetime import datetime

    now = datetime.utcnow()
    started = document.indexing_started_at or document.created_at
    if not started:
        return None

    elapsed = (now - started).total_seconds()

    if document.indexing_stage == "queued" and elapsed > QUEUED_STALE_SECONDS:
        from app.services.ingestion_queue import build_stale_queued_message

        return build_stale_queued_message(document, int(elapsed))

    if elapsed > MAX_INDEXING_SECONDS:
        return (
            f"Indexing exceeded {MAX_INDEXING_SECONDS // 60} minutes at stage "
            f"'{document.indexing_stage or 'unknown'}'. "
            "Check logs for [EMBEDDING_*], [SLOW_STAGE], or [ERROR]."
        )
    return None
