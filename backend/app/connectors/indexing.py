"""Index connector content as workspace documents."""

from __future__ import annotations

import os
import tempfile
from typing import Any

from sqlalchemy.orm import Session

from app.models.document import DocumentCollection, DocumentRecord
from app.models.user import User


def ensure_connector_collection(
    db: Session,
    *,
    user_id: int,
    workspace_id: str,
    name: str,
) -> DocumentCollection:
    collection = (
        db.query(DocumentCollection)
        .filter(
            DocumentCollection.user_id == user_id,
            DocumentCollection.workspace_id == workspace_id,
            DocumentCollection.name == name,
        )
        .first()
    )
    if collection:
        return collection
    collection = DocumentCollection(user_id=user_id, workspace_id=workspace_id, name=name)
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection


def index_connector_text(
    db: Session,
    *,
    user: User,
    collection_id: int,
    workspace_id: str,
    source_key: str,
    filename: str,
    text: str,
) -> DocumentRecord:
    existing = (
        db.query(DocumentRecord)
        .filter(
            DocumentRecord.user_id == user.id,
            DocumentRecord.collection_id == collection_id,
            DocumentRecord.filename == filename,
        )
        .first()
    )
    if existing and existing.storage_path and os.path.isfile(existing.storage_path):
        with open(existing.storage_path, "w", encoding="utf-8") as handle:
            handle.write(text)
        existing.file_size = len(text.encode("utf-8"))
        existing.indexing_stage = "queued"
        db.commit()
        document = existing
    else:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            tmp.write(text)
            storage_path = tmp.name
        document = DocumentRecord(
            user_id=user.id,
            workspace_id=workspace_id,
            collection_id=collection_id,
            filename=filename,
            storage_path=storage_path,
            file_size=len(text.encode("utf-8")),
            indexing_stage="queued",
            security_status="approved",
        )
        db.add(document)
        db.commit()
        db.refresh(document)

    from app.core.app_settings import get_settings
    from app.services.ingestion_queue import dispatch_document_ingestion, ingest_queue_enabled
    from app.services.ingestion_service import run_ingest_document_record

    settings = get_settings()
    if settings.INGEST_IN_BACKGROUND and ingest_queue_enabled():
        dispatch_document_ingestion(db, document.id)
    else:
        run_ingest_document_record(db, document.id)
    return document
