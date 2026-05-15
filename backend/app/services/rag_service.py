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

collection = client.get_collection(
    name=settings.COLLECTION_NAME
)

# -----------------------------------
# RETRIEVE CONTEXT
# -----------------------------------

from app.services.hybrid_search import (
    hybrid_search
)

def retrieve_context(
    query: str
):

    chunks = hybrid_search(
        query=query,
        top_k=10
    )

    reranked_chunks = rerank_documents(
        query=query,
        documents=chunks,
        top_k=3
    )

    context = "\n\n".join(
        reranked_chunks
    )

    return context

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
    history=""
):

    prompt = f"""
You are an AI assistant.

Use:
1. Conversation history
2. Retrieved context

to answer accurately.

-----------------------------------
CONVERSATION HISTORY:
{history}

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