import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.core.chroma_client import get_chroma_client, get_or_create_collection
from sentence_transformers import SentenceTransformer

from app.rag.ingest import load_document, DATA_PATH
from app.rag.chunker import chunk_text

model = SentenceTransformer("BAAI/bge-small-en-v1.5")

client = get_chroma_client("./chroma_db")
collection = get_or_create_collection("omniai_docs")

document = load_document(DATA_PATH)

chunks = chunk_text(document, chunk_size=300, overlap=50)

embeddings = model.encode(chunks).tolist()

collection.add(
    documents=chunks,
    embeddings=embeddings,
    ids=[f"id_{i}" for i in range(len(chunks))],
    metadatas=[
        {"source": "document.txt", "topic": "ai", "chunk_index": i}
        for i in range(len(chunks))
    ],
)
