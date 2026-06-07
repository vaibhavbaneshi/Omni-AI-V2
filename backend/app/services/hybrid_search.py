from rank_bm25 import BM25Okapi

from app.core.app_settings import get_settings
from app.core.chroma_client import get_or_create_collection
from app.services.embedding_service import encode_query

_RRF_K = 60


def _collection():
    settings = get_settings()
    return get_or_create_collection(settings.COLLECTION_NAME)

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
    if user_id is None:
        return {"documents": [], "metadatas": []}

    where_filter = build_filter(
        user_id=user_id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        session_id=session_id,
    )

    if where_filter:
        return _collection().get(
            where=where_filter,
            include=[
                "documents",
                "metadatas"
            ]
        )

    return {"documents": [], "metadatas": []}

# -----------------------------------
# BM25 SEARCH
# -----------------------------------

def bm25_search_ranked(
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

    bm25 = BM25Okapi([doc.split() for doc in documents])
    tokenized_query = query.split()
    scores = bm25.get_scores(tokenized_query)

    ranked = sorted(zip(documents, scores), key=lambda item: item[1], reverse=True)
    return ranked[:top_k]


def bm25_search(
    query,
    top_k=3,
    user_id=None,
    workspace_id="default",
    collection_id=None,
    session_id=None,
):
    return [doc for doc, _ in bm25_search_ranked(
        query,
        top_k=top_k,
        user_id=user_id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        session_id=session_id,
    )]

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
    if user_id is None:
        return []

    embedding = encode_query(query)

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

    results = _collection().query(**query_args)

    return results["documents"][0]

# -----------------------------------
# HYBRID SEARCH
# -----------------------------------

def hybrid_search_ranked(
    query,
    top_k=5,
    user_id=None,
    workspace_id="default",
    collection_id=None,
    session_id=None,
):
    """Merge semantic and BM25 rankings with weighted reciprocal rank fusion."""
    settings = get_settings()
    semantic_weight = settings.HYBRID_SEMANTIC_WEIGHT
    bm25_weight = settings.HYBRID_BM25_WEIGHT

    semantic_results = semantic_search(
        query,
        top_k=max(top_k, 10),
        user_id=user_id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        session_id=session_id,
    )
    bm25_results = bm25_search_ranked(
        query,
        top_k=max(top_k, 10),
        user_id=user_id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        session_id=session_id,
    )

    fused_scores: dict[str, float] = {}

    for rank, document in enumerate(semantic_results):
        fused_scores[document] = fused_scores.get(document, 0.0) + (
            semantic_weight / (_RRF_K + rank + 1)
        )

    for rank, (document, _score) in enumerate(bm25_results):
        fused_scores[document] = fused_scores.get(document, 0.0) + (
            bm25_weight / (_RRF_K + rank + 1)
        )

    ranked = sorted(fused_scores.items(), key=lambda item: item[1], reverse=True)
    return [(document, round(score, 6)) for document, score in ranked[:top_k]]


def hybrid_search(
    query,
    top_k=5,
    user_id=None,
    workspace_id="default",
    collection_id=None,
    session_id=None,
):
    return [document for document, _ in hybrid_search_ranked(
        query,
        top_k=top_k,
        user_id=user_id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        session_id=session_id,
    )]


def semantic_search_with_metadata(
    query,
    top_k=5,
    user_id=None,
    workspace_id="default",
    collection_id=None,
    session_id=None,
):
    if user_id is None:
        return []

    embedding = encode_query(query)

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

    results = _collection().query(**query_args)

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
