"""Background document ingestion worker."""

from __future__ import annotations

import logging
import os
import time

from app.db.session import SessionLocal
from app.models.document import DocumentRecord
from app.services.documents_services import process_document
from app.services.usage_tracking_service import record_ingestion_event

logger = logging.getLogger(__name__)


def ingest_document_record(document_id: int) -> None:
    db = SessionLocal()
    started = time.perf_counter()
    document = None

    try:
        document = (
            db.query(DocumentRecord)
            .filter(DocumentRecord.id == document_id)
            .first()
        )
        if not document:
            logger.warning("Skipping ingestion for missing document_id=%s", document_id)
            return

        if not document.storage_path or not os.path.exists(document.storage_path):
            raise FileNotFoundError("Uploaded file is no longer available on disk.")

        logger.info(
            "Starting document ingestion document_id=%s filename=%s size=%s path=%s user_id=%s session_id=%s",
            document.id,
            document.filename,
            document.file_size,
            document.storage_path,
            document.user_id,
            document.session_id,
        )

        chunk_count = process_document(
            file_path=document.storage_path,
            filename=document.filename,
            user_id=document.user_id,
            workspace_id=document.workspace_id,
            collection_id=document.collection_id,
            session_id=document.session_id,
            document_id=document.id,
        )
        document.chunks_created = chunk_count
        db.commit()

        record_ingestion_event(
            user_id=document.user_id,
            filename=document.filename,
            chunks_created=chunk_count,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            success=True,
        )
        logger.info(
            "Indexed document_id=%s filename=%s chunks=%s duration_ms=%.0f",
            document.id,
            document.filename,
            chunk_count,
            (time.perf_counter() - started) * 1000,
        )
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
        logger.exception("Document ingestion failed for document_id=%s", document_id)
        if document:
            try:
                if os.path.exists(document.storage_path):
                    os.remove(document.storage_path)
                    parent = os.path.dirname(document.storage_path)
                    try:
                        os.rmdir(parent)
                    except OSError:
                        pass
                db.delete(document)
                db.commit()
            except Exception:
                db.rollback()
    finally:
        if document and document.storage_path and os.path.exists(document.storage_path):
            try:
                os.remove(document.storage_path)
                parent = os.path.dirname(document.storage_path)
                try:
                    os.rmdir(parent)
                except OSError:
                    pass
                logger.info(
                    "Cleaned temporary upload file document_id=%s path=%s",
                    document.id,
                    document.storage_path,
                )
            except Exception:
                logger.exception(
                    "Failed to clean temporary upload file document_id=%s path=%s",
                    document.id,
                    document.storage_path,
                )
        db.close()
