"""Embeddings via API (production) or optional local PyTorch (dev only)."""

from __future__ import annotations

import logging
import math
import threading

import httpx

from app.core.app_settings import get_settings

logger = logging.getLogger(__name__)

_model = None
_model_lock = threading.Lock()
_openai_client = None
_openai_lock = threading.Lock()


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _encode_local(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    if not settings.ENABLE_LOCAL_ML and settings.ENVIRONMENT == "production":
        raise RuntimeError("Local embeddings are disabled in production.")

    model = get_embedding_model()
    vectors = model.encode(
        texts,
        batch_size=settings.EMBEDDING_BATCH_SIZE,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return vectors.tolist()


def _get_openai_client():
    global _openai_client
    if _openai_client is not None:
        return _openai_client

    with _openai_lock:
        if _openai_client is None:
            settings = get_settings()
            if not settings.OPENAI_API_KEY.strip():
                raise RuntimeError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
            from openai import OpenAI

            _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return _openai_client


def _encode_openai(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    client = _get_openai_client()
    api_batch = max(1, min(settings.EMBEDDING_BATCH_SIZE, 100))
    all_vectors: list[list[float]] = []

    for start in range(0, len(texts), api_batch):
        batch = texts[start : start + api_batch]
        response = client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=batch,
        )
        ordered = sorted(response.data, key=lambda item: item.index)
        all_vectors.extend(item.embedding for item in ordered)

    return all_vectors


def _encode_huggingface(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    api_key = settings.huggingface_api_key
    if not api_key:
        raise RuntimeError(
            "HUGGINGFACE_API_KEY or HF_TOKEN is required when EMBEDDING_PROVIDER=huggingface"
        )

    model = settings.EMBEDDING_MODEL
    url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{model}"
    api_batch = max(1, min(settings.EMBEDDING_BATCH_SIZE, 32))
    all_vectors: list[list[float]] = []

    with httpx.Client(timeout=120.0) as client:
        for start in range(0, len(texts), api_batch):
            batch = texts[start : start + api_batch]
            response = client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                json={"inputs": batch, "options": {"wait_for_model": True}},
            )
            response.raise_for_status()
            payload = response.json()

            if len(batch) == 1 and payload and isinstance(payload[0], (int, float)):
                batch_vectors = [payload]
            else:
                batch_vectors = payload

            all_vectors.extend(_l2_normalize(vector) for vector in batch_vectors)

    return all_vectors


def get_embedding_model():
    """Lazy-load local SentenceTransformer (requires requirements-local-ml.txt)."""
    global _model
    if get_settings().EMBEDDING_PROVIDER != "local":
        raise RuntimeError(
            f"Local embedding model is disabled (EMBEDDING_PROVIDER={get_settings().EMBEDDING_PROVIDER})"
        )

    if _model is not None:
        return _model

    with _model_lock:
        if _model is None:
            settings = get_settings()
            logger.info("Loading local embedding model: %s", settings.EMBEDDING_MODEL)
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "sentence-transformers is not installed. "
                    "Run: pip install -r requirements-local-ml.txt"
                ) from exc

            _model = SentenceTransformer(settings.EMBEDDING_MODEL)
            logger.info("Local embedding model ready")
        return _model


def preload_embedding_model() -> None:
    """Warm local model only — no-op for API providers."""
    if get_settings().EMBEDDING_PROVIDER != "local":
        return
    try:
        get_embedding_model()
    except Exception as exc:
        logger.warning("Embedding model preload failed: %s", exc)


def encode_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    provider = get_settings().EMBEDDING_PROVIDER
    if provider == "openai":
        return _encode_openai(texts)
    if provider == "huggingface":
        return _encode_huggingface(texts)
    return _encode_local(texts)


def encode_query(text: str) -> list[float]:
    return encode_texts([text])[0]
