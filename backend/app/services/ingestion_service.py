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


def ingest_document_record(document_id: int) -> None:
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
                mark_indexing_failed(db, document.id, str(exc))
            except Exception:
                db.rollback()
                logger.exception(
                    "Failed to persist indexing failure document_id=%s",
                    document.id,
                )
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

    if not document.indexing_started_at:
        return None

    from datetime import datetime

    elapsed = (datetime.utcnow() - document.indexing_started_at).total_seconds()
    if elapsed > MAX_INDEXING_SECONDS:
        return (
            f"Indexing exceeded {MAX_INDEXING_SECONDS // 60} minutes. "
            "Check Railway logs for [EMBEDDING_*] or [ERROR] events."
        )
    return None
