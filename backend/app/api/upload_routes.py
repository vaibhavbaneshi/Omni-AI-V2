import os
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
from app.core.upload_validation import validate_document_upload
from app.core.telemetry import traced_span
from app.services.ingestion_service import ingest_document_record
from app.services.usage_tracking_service import record_ingestion_event
from app.db.session import get_db
from app.models.document import DocumentCollection, DocumentRecord
from app.models.user import User
from sqlalchemy.orm import Session

router = APIRouter()

UPLOAD_DIR = "uploads"

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
    await validate_document_upload(file, max_bytes=get_settings().MAX_UPLOAD_BYTES)

    if session_id is not None:
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

    user_upload_dir = os.path.join(
        UPLOAD_DIR,
        str(current_user.id),
        workspace_id
    )

    os.makedirs(user_upload_dir, exist_ok=True)

    safe_name = os.path.basename(file.filename)
    file_path = os.path.join(
        user_upload_dir,
        safe_name
    )

    with open(file_path, "wb") as f:

        content = await file.read()

        f.write(content)

    document = DocumentRecord(
        user_id=current_user.id,
        workspace_id=workspace_id,
        collection_id=collection_record.id,
        session_id=session_id,
        filename=safe_name,
        storage_path=file_path,
        chunks_created=0,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    settings = get_settings()
    if settings.INGEST_IN_BACKGROUND:
        background_tasks.add_task(ingest_document_record, document.id)
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
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        db.delete(document)
        db.commit()

        raise HTTPException(
            status_code=400,
            detail=str(e)
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
    query = (
        db.query(DocumentRecord)
        .filter(
            DocumentRecord.user_id == current_user.id,
            DocumentRecord.workspace_id == workspace_id,
        )
    )

    if collection_id is not None:
        query = query.filter(DocumentRecord.collection_id == collection_id)

    if session_id is not None:
        query = query.filter(DocumentRecord.session_id == session_id)

    records = query.order_by(DocumentRecord.created_at.desc()).all()

    return {
        "documents": [
            {
                "id": document.id,
                "filename": document.filename,
                "size": os.path.getsize(document.storage_path) if os.path.exists(document.storage_path) else 0,
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
