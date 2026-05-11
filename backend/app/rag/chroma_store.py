import chromadb
from sentence_transformers import SentenceTransformer


from backend.app.rag.ingest import load_document, DATA_PATH
from backend.app.rag.chunker import chunk_text

model = SentenceTransformer("BAAI/bge-small-en-v1.5")

client = chromadb.Client()

client = chromadb.PersistentClient(
    path="./chroma_db"
)

collection = client.create_collection(name="omniai_docs")

document = load_document(DATA_PATH)

chunks = chunk_text(document, chunk_size=300, overlap=50)

embeddings = model.encode(chunks).tolist()

collection.add(
    documents=chunks,
    embeddings=embeddings,
    ids=[f"id_{i}" for i in range(len(chunks))],

    metadatas=
    [
        {"source": "document.txt","topic": "ai", "chunk_index": i}
        for i in range(len(chunks))
    ]
)