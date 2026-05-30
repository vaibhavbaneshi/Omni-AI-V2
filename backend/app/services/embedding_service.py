"""Shared embedding model — lazy-loaded singleton with batched encoding."""

from __future__ import annotations

import logging
import threading

from app.core.app_settings import get_settings

logger = logging.getLogger(__name__)

_model = None
_model_lock = threading.Lock()


def get_embedding_model():
    global _model
    if _model is not None:
        return _model

    with _model_lock:
        if _model is None:
            settings = get_settings()
            logger.info("Loading embedding model: %s", settings.EMBEDDING_MODEL)
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer(settings.EMBEDDING_MODEL)
            logger.info("Embedding model ready")
        return _model


def preload_embedding_model() -> None:
    """Warm the embedding model (call from startup in a background thread)."""
    try:
        get_embedding_model()
    except Exception as exc:
        logger.warning("Embedding model preload failed: %s", exc)


def encode_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    settings = get_settings()
    model = get_embedding_model()
    vectors = model.encode(
        texts,
        batch_size=settings.EMBEDDING_BATCH_SIZE,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return vectors.tolist()


def encode_query(text: str) -> list[float]:
    return encode_texts([text])[0]
