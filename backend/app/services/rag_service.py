import chromadb
import requests
import logging

from sentence_transformers import (
    SentenceTransformer
)

from app.core.config import settings
from app.core.ollama import raise_ollama_http_error, resolve_ollama_model_name
from app.services.prompt_builder import build_stream_prompt

from app.services.reranker_service import (
    rerank_documents
)

logger = logging.getLogger(__name__)

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

from app.core.sanitize import sanitize_retrieved_context
from app.core.telemetry import traced_span
from app.services.retrieval_cache import (
    cache_retrieval_result,
    get_retrieval_cache,
)


def retrieve_context(
    query: str,
    user_id=None,
    workspace_id="default",
    collection_id=None
):
    cached = get_retrieval_cache(
        query=query,
        user_id=user_id,
        workspace_id=workspace_id,
        collection_id=collection_id,
    )
    if cached is not None:
        return cached

    with traced_span("retrieval.hybrid", user_id=user_id, workspace_id=workspace_id):
        chunks = hybrid_search(
            query=query,
            top_k=10,
            user_id=user_id,
            workspace_id=workspace_id,
            collection_id=collection_id,
        )

    if not chunks:
        return ""

    reranked_chunks = rerank_documents(
        query=query,
        documents=chunks,
        top_k=3
    )

    context = sanitize_retrieved_context(reranked_chunks)
    cache_retrieval_result(
        query=query,
        user_id=user_id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        value=context,
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

    prompt = build_stream_prompt(
        query=query,
        context=context or "",
        history="",
        summary="",
        mode="research",
    )

    ollama_url = settings.OLLAMA_URL
    if not ollama_url:
        raise RuntimeError(
            "OLLAMA_URL is not configured. Set OLLAMA_URL to your Ollama base URL "
            "(e.g. http://localhost:11434) or full generate URL."
        )

    model = resolve_ollama_model_name(settings.MODEL_NAME, ollama_url)

    try:
        response = requests.post(
            ollama_url,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.35,
                },
            },
            timeout=120
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise_ollama_http_error(exc, generate_url=ollama_url, model=model)
    except requests.RequestException as exc:
        logger.exception("Error contacting model server at %s", ollama_url)
        raise RuntimeError(
            f"Failed to contact model server at {ollama_url}: {exc}. "
            "Ensure Ollama is running (`ollama serve`)."
        ) from exc

    data = response.json()

    return data.get("response", "")

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
    route=None,
):
    # Route metadata is exposed to the UI via stream meta events, not in the model prompt.
    _ = route

    prompt = build_stream_prompt(
        query=query,
        context=context or "",
        history=history or "",
        summary=summary or "",
        mode=mode or "research",
    )

    ollama_url = settings.OLLAMA_URL
    if not ollama_url:
        raise RuntimeError(
            "OLLAMA_URL is not configured. Set OLLAMA_URL to your Ollama base URL "
            "(e.g. http://localhost:11434) or full generate URL."
        )

    model = resolve_ollama_model_name(settings.MODEL_NAME, ollama_url)

    try:
        response = requests.post(
            ollama_url,
            json={
                "model": model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": 0.35,
                },
            },
            stream=True,
            timeout=120
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise_ollama_http_error(exc, generate_url=ollama_url, model=model)
    except requests.RequestException as exc:
        logger.exception("Error contacting model server at %s", ollama_url)
        raise RuntimeError(
            f"Failed to contact model server at {ollama_url}: {exc}. "
            "Ensure Ollama is running (`ollama serve`)."
        ) from exc

    for line in response.iter_lines():
        if line:
            try:
                data = json.loads(line)
            except Exception:
                # ignore malformed lines but log them
                logger.exception("Failed to parse line from model stream")
                continue

            token = data.get("response", "")
            yield token
