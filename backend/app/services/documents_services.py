import gc
import logging
import os
import uuid

from langchain.text_splitter import RecursiveCharacterTextSplitter
from sqlalchemy.orm import Session

from app.core.app_settings import get_settings
from app.core.chroma_client import get_or_create_collection
from app.core.sanitize import detect_prompt_injection
from app.services.document_loaders import LoadedDocumentPart, load_document_parts
from app.services.embedding_service import encode_texts
from app.services.indexing_progress import update_indexing_progress
from app.services.ingestion_telemetry import IngestionContext

logger = logging.getLogger(__name__)


def get_document_collection():
    settings = get_settings()
    return get_or_create_collection(settings.COLLECTION_NAME)


def chunk_text(text: str) -> list[str]:
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.INGEST_CHUNK_SIZE,
        chunk_overlap=settings.INGEST_CHUNK_OVERLAP,
        length_function=len,
    )
    raw_chunks = splitter.split_text(text)

    seen: set[str] = set()
    chunks: list[str] = []
    for chunk in raw_chunks:
        normalized = chunk.strip()
        if len(normalized) < 32:
            continue
        dedupe_key = normalized.lower()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        chunks.append(normalized)

    if len(chunks) > settings.INGEST_MAX_CHUNKS:
        logger.warning(
            "Truncating document from %s to %s chunks (INGEST_MAX_CHUNKS)",
            len(chunks),
            settings.INGEST_MAX_CHUNKS,
        )
        chunks = chunks[: settings.INGEST_MAX_CHUNKS]

    return chunks


def _truncate_parts(parts: list[LoadedDocumentPart], max_chars: int) -> list[LoadedDocumentPart]:
    truncated: list[LoadedDocumentPart] = []
    remaining = max_chars
    for part in parts:
        if remaining <= 0:
            break
        text = part.text[:remaining]
        if text.strip():
            truncated.append(LoadedDocumentPart(text=text, metadata=dict(part.metadata)))
        remaining -= len(text)
    return truncated


def chunk_document_parts(parts: list[LoadedDocumentPart]) -> list[dict]:
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.INGEST_CHUNK_SIZE,
        chunk_overlap=settings.INGEST_CHUNK_OVERLAP,
        length_function=len,
    )
    documents = splitter.create_documents(
        [part.text for part in parts],
        metadatas=[dict(part.metadata) for part in parts],
    )

    seen: set[str] = set()
    chunks: list[dict] = []
    for document in documents:
        normalized = document.page_content.strip()
        if len(normalized) < 32:
            continue
        dedupe_key = normalized.lower()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        chunks.append({"text": normalized, "metadata": dict(document.metadata or {})})

    if len(chunks) > settings.INGEST_MAX_CHUNKS:
        logger.warning(
            "Truncating document from %s to %s chunks (INGEST_MAX_CHUNKS)",
            len(chunks),
            settings.INGEST_MAX_CHUNKS,
        )
        chunks = chunks[: settings.INGEST_MAX_CHUNKS]

    return chunks


def store_chunks(
    chunks,
    filename,
    user_id,
    workspace_id="default",
    collection_id=None,
    session_id=None,
    document_id=None,
    db: Session | None = None,
    telemetry: IngestionContext | None = None,
):
    if not chunks:
        return

    settings = get_settings()
    collection = get_document_collection()
    batch_size = max(1, settings.CHROMA_ADD_BATCH_SIZE)
    total = len(chunks)

    if db is not None and document_id is not None:
        update_indexing_progress(db, document_id, stage="embedding")

    for start in range(0, total, batch_size):
        raw_batch = chunks[start : start + batch_size]
        batch = [item["text"] if isinstance(item, dict) else item for item in raw_batch]
        batch_num = start // batch_size + 1
        batch_total = (total + batch_size - 1) // batch_size

        if telemetry:
            telemetry.log(
                "EMBEDDING_PROGRESS",
                batch=batch_num,
                batch_total=batch_total,
                processed=start,
                remaining=max(total - start, 0),
                batch_size=len(batch),
            )

        embeddings = encode_texts(
            batch,
            telemetry=telemetry,
            batch_index=batch_num,
            batch_total=batch_total,
        )

        if db is not None and document_id is not None:
            update_indexing_progress(
                db,
                document_id,
                stage="vector_store",
                embeddings_completed=min(start + len(batch), total),
            )

        ids = [str(uuid.uuid4()) for _ in batch]
        metadatas = [
            {
                "source": filename,
                "filename": filename,
                "user_id": str(user_id),
                "workspace_id": workspace_id,
                "collection_id": str(collection_id or "default"),
                "session_id": str(session_id or ""),
                "document_id": str(document_id or ""),
                "chunk_index": start + index,
                "chunk_id": f"{document_id or filename}:{start + index}",
                "embedding_version": settings.embedding_model_label,
                **(
                    raw_batch[index].get("metadata", {})
                    if isinstance(raw_batch[index], dict)
                    else {}
                ),
            }
            for index, _ in enumerate(batch)
        ]

        if telemetry:
            telemetry.log(
                "VECTOR_DB_INSERT_START",
                batch=batch_num,
                batch_total=batch_total,
                vector_count=len(batch),
            )

        collection.add(
            documents=batch,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
        )

        if telemetry:
            telemetry.log(
                "VECTOR_DB_INSERT_COMPLETE",
                batch=batch_num,
                batch_total=batch_total,
                vector_count=len(batch),
            )

        del embeddings, batch, ids, metadatas
        gc.collect()


def process_document(
    file_path: str,
    filename: str,
    user_id: int,
    workspace_id: str = "default",
    collection_id: int | None = None,
    session_id: int | None = None,
    document_id: int | None = None,
    db: Session | None = None,
    telemetry: IngestionContext | None = None,
):
    if telemetry:
        with telemetry.stage("loading", slow_after_seconds=30):
            parts = load_document_parts(file_path)
            text = "\n\n".join(part.text for part in parts)
            char_count = len(text)
            telemetry.log("DOCUMENT_LOADING_COMPLETE", characters=char_count)
    else:
        parts = load_document_parts(file_path)
        text = "\n\n".join(part.text for part in parts)

    injection_matches = detect_prompt_injection(text)
    if injection_matches:
        logger.warning(
            "Prompt injection patterns detected in uploaded document filename=%s user_id=%s document_id=%s matches=%s",
            filename,
            user_id,
            document_id,
            injection_matches[:5],
        )

    settings = get_settings()
    if len(text) > settings.MAX_INGEST_TEXT_CHARS:
        logger.warning(
            "Truncating document text from %s to %s chars (MAX_INGEST_TEXT_CHARS)",
            len(text),
            settings.MAX_INGEST_TEXT_CHARS,
        )
        parts = _truncate_parts(parts, settings.MAX_INGEST_TEXT_CHARS)
        text = "\n\n".join(part.text for part in parts)

    if db is not None and document_id is not None:
        update_indexing_progress(db, document_id, stage="chunking")

    if telemetry:
        with telemetry.stage("chunking", slow_after_seconds=30):
            chunks = chunk_document_parts(parts)
            telemetry.log("CHUNKING_COMPLETE", chunk_count=len(chunks))
    else:
        chunks = chunk_document_parts(parts)

    del text
    if not chunks:
        raise ValueError("No indexable text chunks were produced from the document.")

    if telemetry:
        with telemetry.stage("embedding", slow_after_seconds=60):
            store_chunks(
                chunks,
                filename=filename,
                user_id=user_id,
                workspace_id=workspace_id,
                collection_id=collection_id,
                session_id=session_id,
                document_id=document_id,
                db=db,
                telemetry=telemetry,
            )
    else:
        store_chunks(
            chunks,
            filename=filename,
            user_id=user_id,
            workspace_id=workspace_id,
            collection_id=collection_id,
            session_id=session_id,
            document_id=document_id,
            db=db,
            telemetry=telemetry,
        )

    return len(chunks)
