"""Optional CrossEncoder reranker — lazy-loaded to avoid OOM on small Railway plans."""

from __future__ import annotations

import logging
import threading

from app.core.app_settings import get_settings

logger = logging.getLogger(__name__)

_reranker = None
_reranker_lock = threading.Lock()


def _get_reranker():
    global _reranker
    if _reranker is not None:
        return _reranker

    with _reranker_lock:
        if _reranker is None:
            settings = get_settings()
            logger.info("Loading reranker model: %s", settings.RERANKER_MODEL)
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as exc:
                raise RuntimeError(
                    "sentence-transformers is not installed. "
                    "Run: pip install -r requirements-local-ml.txt or set ENABLE_RERANKER=false."
                ) from exc

            _reranker = CrossEncoder(settings.RERANKER_MODEL)
            logger.info("Reranker model ready")
        return _reranker


def rerank_documents(query, documents, top_k=3):
    if not documents:
        return []

    settings = get_settings()
    if not settings.ENABLE_RERANKER:
        return list(documents)[:top_k]

    pairs = [[query, doc] for doc in documents]
    reranker = _get_reranker()
    scores = reranker.predict(pairs)

    ranked = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in ranked[:top_k]]
