from rank_bm25 import BM25Okapi

from sentence_transformers import (
    SentenceTransformer
)

from app.core.config import settings
from app.core.chroma_client import get_or_create_collection

# -----------------------------------
# CHROMADB
# -----------------------------------

collection = get_or_create_collection(settings.COLLECTION_NAME)

# -----------------------------------
# EMBEDDING MODEL
# -----------------------------------

embedding_model = SentenceTransformer(
    "BAAI/bge-small-en-v1.5"
)

# -----------------------------------
# GET ALL DOCS
# -----------------------------------

def build_filter(
    user_id=None,
    workspace_id="default",
    collection_id=None,
    session_id=None
):

    filters = []

    if user_id is not None:
        filters.append({"user_id": str(user_id)})

    if workspace_id:
        filters.append({"workspace_id": workspace_id})

    if collection_id is not None:
        filters.append({"collection_id": str(collection_id)})

    if session_id is not None:
        filters.append({"session_id": str(session_id)})

    if len(filters) == 1:
        return filters[0]

    if filters:
        return {
            "$and": filters
        }

    return None


def get_scoped_documents(
    user_id=None,
    workspace_id="default",
    collection_id=None,
    session_id=None,
):

    where_filter = build_filter(
        user_id=user_id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        session_id=session_id,
    )

    if where_filter:
        return collection.get(
            where=where_filter,
            include=[
                "documents",
                "metadatas"
            ]
        )

    return collection.get(
        include=[
            "documents",
            "metadatas"
        ]
    )

# -----------------------------------
# BM25 SEARCH
# -----------------------------------

def bm25_search(
    query,
    top_k=3,
    user_id=None,
    workspace_id="default",
    collection_id=None,
    session_id=None,
):

    scoped = get_scoped_documents(
        user_id=user_id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        session_id=session_id,
    )
    documents = scoped.get("documents", [])

    if not documents:
        return []

    bm25 = BM25Okapi(
        [
            doc.split()
            for doc in documents
        ]
    )

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
    top_k=3,
    user_id=None,
    workspace_id="default",
    collection_id=None,
    session_id=None,
):

    embedding = embedding_model.encode(
        query
    ).tolist()

    where_filter = build_filter(
        user_id=user_id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        session_id=session_id,
    )

    query_args = {
        "query_embeddings": [embedding],
        "n_results": top_k
    }

    if where_filter:
        query_args["where"] = where_filter

    results = collection.query(**query_args)

    return results["documents"][0]

# -----------------------------------
# HYBRID SEARCH
# -----------------------------------

def hybrid_search(
    query,
    top_k=5,
    user_id=None,
    workspace_id="default",
    collection_id=None,
    session_id=None,
):

    semantic_results = semantic_search(
        query,
        user_id=user_id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        session_id=session_id,
    )

    bm25_results = bm25_search(
        query,
        user_id=user_id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        session_id=session_id,
    )

    combined = list(
        dict.fromkeys(
            semantic_results + bm25_results
        )
    )

    return combined[:top_k]


def semantic_search_with_metadata(
    query,
    top_k=5,
    user_id=None,
    workspace_id="default",
    collection_id=None,
    session_id=None,
):

    embedding = embedding_model.encode(
        query
    ).tolist()

    where_filter = build_filter(
        user_id=user_id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        session_id=session_id,
    )

    query_args = {
        "query_embeddings": [embedding],
        "n_results": top_k,
        "include": [
            "documents",
            "metadatas",
            "distances"
        ]
    }

    if where_filter:
        query_args["where"] = where_filter

    results = collection.query(**query_args)

    documents_result = results.get("documents", [[]])[0]
    metadatas_result = results.get("metadatas", [[]])[0]
    distances_result = results.get("distances", [[]])[0]

    sources = []

    for index, document in enumerate(documents_result):

        metadata = metadatas_result[index] if index < len(metadatas_result) else {}
        distance = distances_result[index] if index < len(distances_result) else None

        sources.append(
            {
                "title": metadata.get("source", "Document") if metadata else "Document",
                "source": metadata.get("source", "Document") if metadata else "Document",
                "chunk": document,
                "score": None if distance is None else round(max(0, 1 - distance), 4),
                "strategy": "semantic",
                "type": "document",
                "url": None,
                "metadata": metadata or {}
            }
        )

    return sources
