import os
import uuid

from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.core.chroma_client import get_or_create_collection
from app.services.document_loaders import load_document

embedding_model = SentenceTransformer("BAAI/bge-small-en-v1.5")
collection = get_or_create_collection(settings.COLLECTION_NAME)


def chunk_text(text: str):
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    return splitter.split_text(text)


def store_chunks(
    chunks,
    filename,
    user_id,
    workspace_id="default",
    collection_id=None,
    session_id=None,
    document_id=None,
):
    embeddings = embedding_model.encode(chunks).tolist()

    ids = [str(uuid.uuid4()) for _ in chunks]

    metadatas = [
        {
            "source": filename,
            "filename": filename,
            "user_id": str(user_id),
            "workspace_id": workspace_id,
            "collection_id": str(collection_id or "default"),
            "session_id": str(session_id or ""),
            "document_id": str(document_id or ""),
            "chunk_index": index,
            "embedding_version": "bge-small-en-v1.5",
        }
        for index, _ in enumerate(chunks)
    ]

    collection.add(
        documents=chunks,
        embeddings=embeddings,
        ids=ids,
        metadatas=metadatas,
    )


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
    chunks = chunk_text(text)

    store_chunks(
        chunks=chunks,
        filename=filename,
        user_id=user_id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        session_id=session_id,
        document_id=document_id,
    )

    return len(chunks)
