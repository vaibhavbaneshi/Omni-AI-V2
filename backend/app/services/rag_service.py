import chromadb
import requests

from sentence_transformers import (
    SentenceTransformer
)

from app.core.config import settings

from app.services.reranker_service import (
    rerank_documents
)

from app.services.conversation_service import (
    get_chat_history
)

import json

# -----------------------------------
# EMBEDDING MODEL
# -----------------------------------

embedding_model = SentenceTransformer(
    "BAAI/bge-small-en-v1.5"
)

# -----------------------------------
# CHROMADB
# -----------------------------------

client = chromadb.PersistentClient(
    path=settings.CHROMA_DB_PATH
)

try:
    collection = client.get_collection(name=settings.COLLECTION_NAME)
except Exception:
    collection = client.create_collection(name=settings.COLLECTION_NAME)

# -----------------------------------
# RETRIEVE CONTEXT
# -----------------------------------

from app.services.hybrid_search import (
    hybrid_search,
    semantic_search_with_metadata
)

def retrieve_context(
    query: str,
    user_id=None,
    workspace_id="default",
    collection_id=None
):

    chunks = hybrid_search(
        query=query,
        top_k=10,
        user_id=user_id,
        workspace_id=workspace_id,
        collection_id=collection_id
    )

    if not chunks:
        return ""

    reranked_chunks = rerank_documents(
        query=query,
        documents=chunks,
        top_k=3
    )

    context = "\n\n".join(
        reranked_chunks
    )

    return context


def retrieve_context_details(
    query: str,
    user_id=None,
    workspace_id="default",
    collection_id=None
):

    sources = semantic_search_with_metadata(
        query=query,
        top_k=5,
        user_id=user_id,
        workspace_id=workspace_id,
        collection_id=collection_id
    )

    chunks = [
        source["chunk"]
        for source in sources
        if source.get("chunk")
    ]

    reranked_chunks = rerank_documents(
        query=query,
        documents=chunks,
        top_k=3
    ) if chunks else []

    context = "\n\n".join(
        reranked_chunks
    )

    ranked_sources = []

    for chunk in reranked_chunks:

        source = next(
            (
                item
                for item in sources
                if item.get("chunk") == chunk
            ),
            None
        )

        if source:
            ranked_sources.append(source)

    return {
        "context": context,
        "sources": ranked_sources,
        "strategy": "hybrid-semantic-rerank",
        "chunks": len(ranked_sources)
    }

# -----------------------------------
# GENERATE RESPONSE
# -----------------------------------

def generate_response(
    query: str,
    context: str
):

    prompt = f"""
You are an AI assistant.

Answer ONLY using the provided context.

Context:
{context}

Question:
{query}
"""

    response = requests.post(
        settings.OLLAMA_URL,
        json={
            "model": settings.MODEL_NAME,
            "prompt": prompt,
            "stream": False
        }
    )

    data = response.json()

    return data["response"]

# -----------------------------------
# COMPLETE RAG PIPELINE
# -----------------------------------

def chat_with_rag(query: str):

    context = retrieve_context(query)

    response = generate_response(
        query=query,
        context=context
    )

    return {
        "query": query,
        "context": context,
        "response": response
    }

# -----------------------------------
# STREAM RESPONSE
# -----------------------------------

def stream_response(
    query,
    context,
    history="",
    summary="",
    mode="research",
    route=None
):

    mode_prompts = {
        "research": """
Use a research-focused style:
- lead with a direct answer
- organize into clear sections
- cite sources inline when source labels are present
- call out uncertainty and source limitations
""",
        "coding": """
Use a coding-focused style:
- prioritize implementation details
- include concise code examples when useful
- explain tradeoffs and edge cases
- keep prose tight
""",
        "writing": """
Use a writing-focused style:
- improve clarity, structure, and tone
- preserve the user's intent
- offer polished wording and alternatives when useful
""",
        "analyst": """
Use an analyst-focused style:
- structure findings, evidence, and implications
- compare options where relevant
- include assumptions and risks
"""
    }

    mode_instruction = mode_prompts.get(
        mode,
        mode_prompts["research"]
    )

    route_summary = ""

    if route:
        route_summary = f"""
ROUTING PLAN:
Strategy: {route.get("strategy", "unknown")}
Tools used: {", ".join(route.get("tools", []))}
Status: {route.get("status", "ready")}
"""

    prompt = f"""
You are an AI assistant.

Use:
1. Conversation history
2. Retrieved context

to answer accurately.

Do not reveal hidden reasoning or private chain-of-thought.
You may briefly mention high-level tool usage and evidence quality.

{mode_instruction}

-----------------------------------
CONVERSATION HISTORY:
{history}

-----------------------------------
CONVERSATION SUMMARY:
{summary}

-----------------------------------
{route_summary}

-----------------------------------
RETRIEVED CONTEXT:
{context}

-----------------------------------
QUESTION:
{query}
"""

    response = requests.post(
        settings.OLLAMA_URL,
        json={
            "model": settings.MODEL_NAME,
            "prompt": prompt,
            "stream": True
        },
        stream=True
    )

    for line in response.iter_lines():

        if line:

            data = json.loads(line)

            token = data.get(
                "response",
                ""
            )

            yield token
