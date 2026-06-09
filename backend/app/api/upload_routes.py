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
    Query,
)
from pydantic import ValidationError

from app.services.document_loaders import DocumentLoadError
from app.services.documents_services import get_document_collection

from app.core.upload_storage import create_upload_directory
from app.core.security import get_current_user
from app.core.app_settings import get_settings
from app.core.upload_validation import sanitize_upload_filename, validate_document_upload
from app.services.upload_security_service import (
    UploadSecurityError,
    move_to_storage,
    process_upload_security,
    quarantine_directory,
)
from app.services.indexing_progress import document_status_payload, update_indexing_progress
from app.services.ingestion_service import detect_stale_indexing, run_ingest_document_record
from app.services.ingestion_queue import (
    dispatch_document_ingestion,
    ingest_queue_enabled,
    should_use_background_tasks,
    try_recover_stuck_queued_document,
)
from app.services.usage_tracking_service import record_ingestion_event
from app.services.file_scanner import FileScanError, scan_uploaded_file
from app.services.security_audit_service import audit_log
from app.db.session import get_db
from app.models.document import DocumentCollection, DocumentRecord
from app.models.user import User
from app.schemas.upload_schemas import UploadFormParams
from app.schemas.workspace_schemas import CollectionUpdate, MoveDocumentRequest
from app.services.collection_service import (
    collection_document_count,
    delete_collection,
    move_document_to_collection,
    update_collection_name,
)
from sqlalchemy.orm import Session

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload")

async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    workspace_id: str = Query(default="default"),
    collection_id: int | None = Query(default=None),
    session_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        form_params = UploadFormParams(
            workspace_id=workspace_id,
            collection_id=collection_id,
            session_id=session_id,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    workspace_id = form_params.workspace_id
    collection_id = form_params.collection_id
    session_id = form_params.session_id

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
    quarantine_dir = quarantine_directory(current_user.id, session_id)

    safe_name = sanitize_upload_filename(file.filename)
    quarantine_path = os.path.join(quarantine_dir, safe_name)
    file_path = os.path.join(user_upload_dir, safe_name)

    try:
        content = await file.read()
        with open(quarantine_path, "wb") as f:
            f.write(content)
        logger.info(
            "Upload quarantined filename=%s size=%s user_id=%s session_id=%s",
            safe_name,
            len(content),
            current_user.id,
            session_id,
        )
        process_upload_security(
            quarantine_path=quarantine_path,
            filename=safe_name,
            content_type=file.content_type,
            user_id=current_user.id,
        )
        move_to_storage(quarantine_path, file_path)
    except FileScanError as exc:
        for path in (quarantine_path, file_path):
            if os.path.exists(path):
                os.remove(path)
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
    except UploadSecurityError as exc:
        if os.path.exists(quarantine_path):
            os.remove(quarantine_path)
        audit_log(
            db,
            action="upload.rejected.security",
            user_id=current_user.id,
            detail={"filename": safe_name, "reason": str(exc), "session_id": session_id},
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
        security_status="approved",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    if settings.INGEST_IN_BACKGROUND:
        if ingest_queue_enabled():
            dispatch = dispatch_document_ingestion(db, document.id)
            logger.info(
                "[INGEST_QUEUED] document_id=%s job_id=%s filename=%s size=%s user_id=%s session_id=%s "
                "storage_path=%s embedding_provider=%s dispatch=%s worker_count=%s",
                document.id,
                dispatch.get("job_id"),
                safe_name,
                file_size,
                current_user.id,
                session_id,
                file_path,
                settings.EMBEDDING_PROVIDER,
                dispatch.get("dispatch"),
                dispatch.get("worker_count"),
            )
            response: dict = {
                "message": "Document uploaded. Indexing in background.",
                "filename": safe_name,
                "chunks_created": 0,
                "indexing": True,
                "collection_id": collection_record.id,
                "document_id": document.id,
                "job_id": dispatch.get("job_id"),
                "worker_count": dispatch.get("worker_count"),
                "dispatch": dispatch.get("dispatch"),
            }
            if dispatch.get("warning"):
                response["warning"] = dispatch["warning"]
            return response
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
    if session_id is None and collection_id is None:
        return {"documents": []}

    query = (
        db.query(DocumentRecord)
        .filter(
            DocumentRecord.user_id == current_user.id,
            DocumentRecord.workspace_id == workspace_id,
        )
    )

    if session_id is not None:
        query = query.filter(DocumentRecord.session_id == session_id)
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
        if ingest_queue_enabled():
            from app.services.ingestion_queue import get_active_worker_count, get_ingest_job_info

            payload["worker_count"] = get_active_worker_count()
            if document.indexing_job_id:
                payload["job"] = get_ingest_job_info(document.indexing_job_id)
            if payload.get("worker_count") == 0 and try_recover_stuck_queued_document(document.id):
                payload["recovery"] = "inline_ingest_started"
                payload["stale_message"] = (
                    f"{stale_message} Recovery: started in-process indexing in the API container."
                )
        logger.warning(
            "[INGEST_STALE] document_id=%s job_id=%s stage=%s elapsed=%s worker_count=%s message=%s",
            document.id,
            document.indexing_job_id,
            document.indexing_stage,
            payload.get("elapsed_seconds"),
            payload.get("worker_count"),
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
                "document_count": collection_document_count(db, collection_id=collection_item.id),
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


@router.patch("/collections/{collection_id}")
def patch_collection(
    collection_id: int,
    body: CollectionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        collection = update_collection_name(
            db,
            user_id=current_user.id,
            collection_id=collection_id,
            name=body.name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found.")

    return {
        "id": collection.id,
        "name": collection.name,
        "workspace_id": collection.workspace_id,
        "document_count": collection_document_count(db, collection_id=collection.id),
    }


@router.delete("/collections/{collection_id}")
def remove_collection(
    collection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        deleted = delete_collection(
            db,
            user_id=current_user.id,
            collection_id=collection_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=404, detail="Collection not found.")

    return {"message": "Collection deleted", "collection_id": collection_id}


@router.patch("/documents/id/{document_id}/collection")
def move_document_collection(
    document_id: int,
    body: MoveDocumentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        document = move_document_to_collection(
            db,
            user_id=current_user.id,
            document_id=document_id,
            collection_id=body.collection_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    return {
        "document_id": document.id,
        "filename": document.filename,
        "collection_id": document.collection_id,
    }
