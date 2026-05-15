from sentence_transformers import (
    CrossEncoder
)

# -----------------------------------
# LOAD RERANKER MODEL
# -----------------------------------

reranker = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

# -----------------------------------
# RERANK DOCUMENTS
# -----------------------------------

def rerank_documents(
    query,
    documents,
    top_k=3
):

    pairs = [
        [query, doc]
        for doc in documents
    ]

    scores = reranker.predict(
        pairs
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