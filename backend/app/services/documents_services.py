import gc
import logging
import os
import uuid

from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.core.app_settings import get_settings
from app.core.chroma_client import get_or_create_collection
from app.core.sanitize import detect_prompt_injection
from app.services.document_loaders import load_document
from app.services.embedding_service import encode_texts

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


def store_chunks(
    chunks,
    filename,
    user_id,
    workspace_id="default",
    collection_id=None,
    session_id=None,
    document_id=None,
):
    if not chunks:
        return

    settings = get_settings()
    collection = get_document_collection()
    batch_size = max(1, settings.CHROMA_ADD_BATCH_SIZE)

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        embeddings = encode_texts(batch)
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
                "embedding_version": settings.embedding_model_label,
            }
            for index, _ in enumerate(batch)
        ]
        collection.add(
            documents=batch,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
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
):
    text = load_document(file_path)
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
        text = text[: settings.MAX_INGEST_TEXT_CHARS]

    chunks = chunk_text(text)
    del text
    if not chunks:
        raise ValueError("No indexable text chunks were produced from the document.")

    store_chunks(
        chunks,
        filename=filename,
        user_id=user_id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        session_id=session_id,
        document_id=document_id,
    )

    return len(chunks)
