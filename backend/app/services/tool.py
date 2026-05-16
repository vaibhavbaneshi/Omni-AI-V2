from app.services.rag_service import (
    retrieve_context
)

from app.services.hybrid_search import (
    hybrid_search
)

# -----------------------------------
# SEMANTIC TOOL
# -----------------------------------

def semantic_tool(query):

    return retrieve_context(query)

# -----------------------------------
# BM25 TOOL
# -----------------------------------

def bm25_tool(query):

    results = hybrid_search(
        query=query,
        top_k=5
    )

    return "\n\n".join(results)

# -----------------------------------
# HYBRID TOOL
# -----------------------------------

def hybrid_tool(query):

    return retrieve_context(query)