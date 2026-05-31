import os
import logging
import tempfile
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
from app.services.documents_services import get_document_collection, process_document

from app.core.security import (
    get_current_user
)
from app.core.app_settings import get_settings
from app.core.upload_validation import sanitize_upload_filename, validate_document_upload
from app.core.telemetry import traced_span
from app.services.ingestion_service import ingest_document_record
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

    user_upload_dir = tempfile.mkdtemp(
        prefix=f"omniai-upload-u{current_user.id}-s{session_id}-",
        dir=tempfile.gettempdir(),
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
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    if settings.INGEST_IN_BACKGROUND:
        background_tasks.add_task(ingest_document_record, document.id)
        logger.info(
            "Upload queued for background indexing document_id=%s filename=%s size=%s user_id=%s session_id=%s",
            document.id,
            safe_name,
            file_size,
            current_user.id,
            session_id,
        )
        return {
            "message": "Document uploaded. Indexing in background.",
            "filename": safe_name,
            "chunks_created": 0,
            "indexing": True,
            "collection_id": collection_record.id,
            "document_id": document.id,
        }

    ingest_started = time.perf_counter()
    try:
        with traced_span(
            "document.ingest",
            user_id=current_user.id,
            filename=safe_name,
            session_id=session_id,
        ):
            chunk_count = process_document(
                file_path=file_path,
                filename=safe_name,
                user_id=current_user.id,
                workspace_id=workspace_id,
                collection_id=collection_record.id,
                session_id=session_id,
                document_id=document.id
            )

        document.chunks_created = chunk_count
        db.commit()
        record_ingestion_event(
            user_id=current_user.id,
            filename=safe_name,
            chunks_created=chunk_count,
            duration_ms=round((time.perf_counter() - ingest_started) * 1000, 2),
            success=True,
        )

    except DocumentLoadError as e:
        record_ingestion_event(
            user_id=current_user.id,
            filename=safe_name,
            chunks_created=0,
            duration_ms=round((time.perf_counter() - ingest_started) * 1000, 2),
            success=False,
            error_message=str(e),
        )
        db.delete(document)
        db.commit()
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.warning(
            "Document processing failed filename=%s document_id=%s user_id=%s session_id=%s error=%s",
            safe_name,
            document.id,
            current_user.id,
            session_id,
            str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        db.delete(document)
        db.commit()
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.exception(
            "Unexpected document processing failure filename=%s document_id=%s user_id=%s session_id=%s",
            safe_name,
            document.id,
            current_user.id,
            session_id,
        )

        raise HTTPException(
            status_code=500,
            detail="Document upload failed during processing. Check backend logs for details."
        ) from e

    if os.path.exists(file_path):
        os.remove(file_path)
        try:
            os.rmdir(user_upload_dir)
        except OSError:
            pass

    logger.info(
        "Upload processed successfully document_id=%s filename=%s size=%s chunks=%s user_id=%s session_id=%s",
        document.id,
        safe_name,
        file_size,
        chunk_count,
        current_user.id,
        session_id,
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
                "id": document.id,
                "filename": document.filename,
                "size": document.file_size
                or (
                    os.path.getsize(document.storage_path)
                    if document.storage_path and os.path.exists(document.storage_path)
                    else 0
                ),
                "updated_at": document.created_at.timestamp() if document.created_at else 0,
                "collection_id": document.collection_id,
                "session_id": document.session_id,
                "chunks_created": document.chunks_created,
                "status": "ready" if document.chunks_created > 0 else "indexing",
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

    return {
        "id": document.id,
        "filename": document.filename,
        "chunks_created": document.chunks_created,
        "status": "ready" if document.chunks_created > 0 else "indexing",
    }


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
