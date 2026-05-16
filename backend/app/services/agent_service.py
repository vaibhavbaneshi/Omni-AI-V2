from app.services.rag_service import (
    retrieve_context
)

# -----------------------------------
# SIMPLE RETRIEVAL AGENT
# -----------------------------------

def retrieval_agent(
    query
):

    query_lower = query.lower()

    # -----------------------------------
    # STRATEGY SELECTION
    # -----------------------------------

    if "exact" in query_lower:

        strategy = "bm25"

    elif (
        "similar" in query_lower
        or
        "meaning" in query_lower
    ):

        strategy = "semantic"

    else:

        strategy = "hybrid"

    # -----------------------------------
    # RETRIEVE
    # -----------------------------------

    context = retrieve_context(
        query=query
    )

    return {
        "strategy": strategy,
        "context": context
    }