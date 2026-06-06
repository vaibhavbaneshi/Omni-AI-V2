import os
import logging
import time

from fastapi import (
    APIRouter,
    BackgroundTasks,
    UploadFile,
    File,
    HTTPException,
    Depends,
)

from app.services.document_loaders import DocumentLoadError
from app.services.documents_services import get_document_collection

from app.core.upload_storage import create_upload_directory
from app.core.security import get_current_user
from app.core.app_settings import get_settings
from app.core.upload_validation import sanitize_upload_filename, validate_document_upload
from app.services.indexing_progress import document_status_payload, update_indexing_progress
from app.services.ingestion_service import detect_stale_indexing, run_ingest_document_record
from app.services.ingestion_queue import (
    enqueue_document_ingestion,
    ingest_queue_enabled,
    should_use_background_tasks,
)
from app.services.usage_tracking_service import record_ingestion_event
from app.services.file_scanner import FileScanError, scan_uploaded_file
from app.services.security_audit_service import audit_log
from app.db.session import get_db
from app.models.document import DocumentCollection, DocumentRecord
from app.models.user import User
from sqlalchemy.orm import Session

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload")

async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    workspace_id: str = "default",
    collection_id: int | None = None,
    session_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    settings = get_settings()
    logger.info(
        "Upload request received filename=%s content_type=%s user_id=%s session_id=%s collection_id=%s",
        file.filename,
        file.content_type,
        current_user.id,
        session_id,
        collection_id,
    )

    try:
        file_size = await validate_document_upload(file, max_bytes=settings.MAX_UPLOAD_BYTES)
    except HTTPException:
        logger.warning(
            "Upload validation failed filename=%s user_id=%s session_id=%s",
            file.filename,
            current_user.id,
            session_id,
            exc_info=True,
        )
        raise

    logger.info(
        "Upload validation passed filename=%s size=%s user_id=%s session_id=%s",
        file.filename,
        file_size,
        current_user.id,
        session_id,
    )

    if session_id is None:
        raise HTTPException(
            status_code=400,
            detail="session_id is required — documents must belong to a chat session.",
        )

    from app.models.chat_session import ChatSession

    owned_session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
        .first()
    )
    if not owned_session:
        raise HTTPException(status_code=404, detail="Session not found")

    collection_record = None

    if collection_id is not None:
        collection_record = (
            db.query(DocumentCollection)
            .filter(
                DocumentCollection.id == collection_id,
                DocumentCollection.user_id == current_user.id
            )
            .first()
        )

        if not collection_record:
            raise HTTPException(
                status_code=404,
                detail="Collection not found"
            )

    if collection_record is None:
        collection_record = (
            db.query(DocumentCollection)
            .filter(
                DocumentCollection.user_id == current_user.id,
                DocumentCollection.workspace_id == workspace_id,
                DocumentCollection.name == "Default"
            )
            .first()
        )

        if collection_record is None:
            collection_record = DocumentCollection(
                user_id=current_user.id,
                workspace_id=workspace_id,
                name="Default"
            )
            db.add(collection_record)
            db.commit()
            db.refresh(collection_record)

    user_upload_dir = create_upload_directory(
        user_id=current_user.id,
        session_id=session_id,
    )

    safe_name = sanitize_upload_filename(file.filename)
    file_path = os.path.join(
        user_upload_dir,
        safe_name
    )

    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        logger.info(
            "Upload stored in temporary file filename=%s size=%s path=%s user_id=%s session_id=%s",
            safe_name,
            len(content),
            file_path,
            current_user.id,
            session_id,
        )
        scan_uploaded_file(file_path, filename=safe_name, user_id=current_user.id)
    except FileScanError as exc:
        if os.path.exists(file_path):
            os.remove(file_path)
        try:
            os.rmdir(user_upload_dir)
        except OSError:
            pass
        audit_log(
            db,
            action="upload.rejected.malware",
            user_id=current_user.id,
            detail={"filename": safe_name, "session_id": session_id},
        )
        logger.warning(
            "Upload virus scan rejected filename=%s user_id=%s session_id=%s",
            safe_name,
            current_user.id,
            session_id,
            exc_info=True,
        )
        raise HTTPException(status_code=400, detail="Uploaded file failed security scanning.") from exc
    except Exception as exc:
        try:
            os.rmdir(user_upload_dir)
        except OSError:
            pass
        logger.exception(
            "Upload storage failed filename=%s path=%s user_id=%s session_id=%s",
            safe_name,
            file_path,
            current_user.id,
            session_id,
        )
        raise HTTPException(status_code=500, detail="Unable to store uploaded file.") from exc

    audit_log(
        db,
        action="upload.received",
        user_id=current_user.id,
        detail={"filename": safe_name, "size": file_size, "session_id": session_id},
    )

    document = DocumentRecord(
        user_id=current_user.id,
        workspace_id=workspace_id,
        collection_id=collection_record.id,
        session_id=session_id,
        filename=safe_name,
        storage_path=file_path,
        file_size=file_size,
        chunks_created=0,
        indexing_stage="queued",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    if settings.INGEST_IN_BACKGROUND:
        if ingest_queue_enabled():
            job_id = enqueue_document_ingestion(db, document.id)
            logger.info(
                "[INGEST_QUEUED] document_id=%s job_id=%s filename=%s size=%s user_id=%s session_id=%s "
                "storage_path=%s embedding_provider=%s dispatch=rq",
                document.id,
                job_id,
                safe_name,
                file_size,
                current_user.id,
                session_id,
                file_path,
                settings.EMBEDDING_PROVIDER,
            )
        elif should_use_background_tasks():
            update_indexing_progress(db, document.id, stage="queued", mark_started=True)
            background_tasks.add_task(run_ingest_document_record, document.id)
            logger.info(
                "[INGEST_QUEUED] document_id=%s filename=%s size=%s user_id=%s session_id=%s "
                "storage_path=%s embedding_provider=%s dispatch=background_tasks",
                document.id,
                safe_name,
                file_size,
                current_user.id,
                session_id,
                file_path,
                settings.EMBEDDING_PROVIDER,
            )
        else:
            raise HTTPException(
                status_code=503,
                detail="Background ingestion is enabled but no dispatch backend is configured.",
            )
        return {
            "message": "Document uploaded. Indexing in background.",
            "filename": safe_name,
            "chunks_created": 0,
            "indexing": True,
            "collection_id": collection_record.id,
            "document_id": document.id,
        }

    logger.info(
        "[INGEST_SYNC_START] document_id=%s filename=%s embedding_provider=%s",
        document.id,
        safe_name,
        settings.EMBEDDING_PROVIDER,
    )
    ingest_started = time.perf_counter()
    try:
        run_ingest_document_record(document.id)
        db.refresh(document)
        if document.indexing_stage == "failed":
            raise HTTPException(
                status_code=400,
                detail=document.indexing_error or "Document indexing failed.",
            )
        chunk_count = document.chunks_created
    except HTTPException:
        raise
    except DocumentLoadError as e:
        record_ingestion_event(
            user_id=current_user.id,
            filename=safe_name,
            chunks_created=0,
            duration_ms=round((time.perf_counter() - ingest_started) * 1000, 2),
            success=False,
            error_message=str(e),
        )
        logger.warning(
            "[INGEST_SYNC_FAILED] document_id=%s error=%s",
            document.id,
            str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception(
            "[INGEST_SYNC_FAILED] document_id=%s unexpected error",
            document.id,
        )
        raise HTTPException(
            status_code=500,
            detail="Document upload failed during processing. Check backend logs for [INGEST_*] lines.",
        ) from e

    logger.info(
        "[INGEST_SYNC_COMPLETE] document_id=%s filename=%s chunks=%s duration_ms=%.0f",
        document.id,
        safe_name,
        chunk_count,
        (time.perf_counter() - ingest_started) * 1000,
    )

    return {
        "message": "Document uploaded successfully",
        "filename": safe_name,
        "chunks_created": chunk_count,
        "indexing": False,
        "collection_id": collection_record.id,
        "document_id": document.id
    }


@router.get("/documents")
def list_documents(
    workspace_id: str = "default",
    collection_id: int | None = None,
    session_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if session_id is None:
        return {"documents": []}

    query = (
        db.query(DocumentRecord)
        .filter(
            DocumentRecord.user_id == current_user.id,
            DocumentRecord.workspace_id == workspace_id,
            DocumentRecord.session_id == session_id,
        )
    )

    if collection_id is not None:
        query = query.filter(DocumentRecord.collection_id == collection_id)

    records = query.order_by(DocumentRecord.created_at.desc()).all()

    return {
        "documents": [
            {
                **document_status_payload(document),
                "size": document.file_size
                or (
                    os.path.getsize(document.storage_path)
                    if document.storage_path and os.path.exists(document.storage_path)
                    else 0
                ),
                "updated_at": document.created_at.timestamp() if document.created_at else 0,
                "collection_id": document.collection_id,
                "session_id": document.session_id,
            }
            for document in records
        ]
    }


def _delete_document_record(document: DocumentRecord, db: Session) -> str:
    safe_name = document.filename

    if os.path.exists(document.storage_path):
        os.remove(document.storage_path)

    matches = get_document_collection().get(
        where={
            "$and": [
                {"source": safe_name},
                {"user_id": str(document.user_id)},
                {"document_id": str(document.id)},
            ]
        }
    )

    ids = matches.get("ids", [])

    if ids:
        get_document_collection().delete(ids=ids)

    db.delete(document)
    db.commit()
    return safe_name


@router.get("/documents/{document_id}/status")
def get_document_status(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = (
        db.query(DocumentRecord)
        .filter(
            DocumentRecord.id == document_id,
            DocumentRecord.user_id == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    payload = document_status_payload(document)
    stale_message = detect_stale_indexing(document)
    if stale_message and payload["status"] == "indexing":
        payload["stale"] = True
        payload["stale_message"] = stale_message
        logger.warning(
            "[INGEST_STALE] document_id=%s stage=%s elapsed=%s message=%s",
            document.id,
            document.indexing_stage,
            payload.get("elapsed_seconds"),
            stale_message,
        )
    return payload


@router.delete("/documents/id/{document_id}")
def delete_document_by_id(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = (
        db.query(DocumentRecord)
        .filter(
            DocumentRecord.id == document_id,
            DocumentRecord.user_id == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    filename = _delete_document_record(document, db)
    audit_log(
        db,
        action="upload.deleted",
        user_id=current_user.id,
        detail={"filename": filename, "document_id": document_id},
    )

    return {
        "message": "Document deleted",
        "filename": filename,
        "document_id": document_id,
    }


@router.delete("/documents/{filename}")
def delete_document(
    filename: str,
    session_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    safe_name = os.path.basename(filename)
    query = db.query(DocumentRecord).filter(
        DocumentRecord.user_id == current_user.id,
        DocumentRecord.filename == safe_name,
    )

    if session_id is not None:
        query = query.filter(DocumentRecord.session_id == session_id)

    document = query.order_by(DocumentRecord.created_at.desc()).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    deleted_name = _delete_document_record(document, db)
    audit_log(
        db,
        action="upload.deleted",
        user_id=current_user.id,
        detail={"filename": deleted_name, "document_id": document.id},
    )

    return {
        "message": "Document deleted",
        "filename": deleted_name,
        "document_id": document.id,
    }


@router.get("/collections")
def list_collections(
    workspace_id: str = "default",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    collections = (
        db.query(DocumentCollection)
        .filter(
            DocumentCollection.user_id == current_user.id,
            DocumentCollection.workspace_id == workspace_id
        )
        .order_by(DocumentCollection.created_at.desc())
        .all()
    )

    return {
        "collections": [
            {
                "id": collection_item.id,
                "name": collection_item.name,
                "workspace_id": collection_item.workspace_id,
                "created_at": collection_item.created_at.isoformat() if collection_item.created_at else None
            }
            for collection_item in collections
        ]
    }


@router.post("/collections")
def create_collection(
    name: str,
    workspace_id: str = "default",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    collection_record = DocumentCollection(
        user_id=current_user.id,
        workspace_id=workspace_id,
        name=name
    )

    db.add(collection_record)
    db.commit()
    db.refresh(collection_record)

    return {
        "id": collection_record.id,
        "name": collection_record.name,
        "workspace_id": collection_record.workspace_id
    }
