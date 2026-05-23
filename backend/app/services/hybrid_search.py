from rank_bm25 import BM25Okapi

import chromadb

from sentence_transformers import (
    SentenceTransformer
)

from app.core.config import settings

# -----------------------------------
# CHROMADB
# -----------------------------------

client = chromadb.PersistentClient(
    path=settings.CHROMA_DB_PATH
)

collection = client.get_collection(
    name=settings.COLLECTION_NAME
)

# -----------------------------------
# EMBEDDING MODEL
# -----------------------------------

embedding_model = SentenceTransformer(
    "BAAI/bge-small-en-v1.5"
)

# -----------------------------------
# GET ALL DOCS
# -----------------------------------

all_docs = collection.get()

documents = all_docs["documents"]

# -----------------------------------
# BM25 INDEX
# -----------------------------------

if not documents:
    tokenized_docs = []
    bm25 = None
else:
    tokenized_docs = [
        doc.split()
        for doc in documents
    ]

    bm25 = BM25Okapi(tokenized_docs)

# -----------------------------------
# BM25 SEARCH
# -----------------------------------

def bm25_search(
    query,
    top_k=3
):

    if not bm25:
        return []

    tokenized_query = query.split()

    scores = bm25.get_scores(
        tokenized_query
    )

    ranked = sorted(
        zip(documents, scores),
        key=lambda x: x[1],
        reverse=True
    )

    return [
        doc[0]
        for doc in ranked[:top_k]
    ]

# -----------------------------------
# SEMANTIC SEARCH
# -----------------------------------

def semantic_search(
    query,
    top_k=3
):

    embedding = embedding_model.encode(
        query
    ).tolist()

    results = collection.query(
        query_embeddings=[embedding],
        n_results=top_k
    )

    return results["documents"][0]

# -----------------------------------
# HYBRID SEARCH
# -----------------------------------

def hybrid_search(
    query,
    top_k=5
):

    semantic_results = semantic_search(
        query
    )

    bm25_results = bm25_search(
        query
    )

    combined = list(
        dict.fromkeys(
            semantic_results + bm25_results
        )
    )

    return combined[:top_k]