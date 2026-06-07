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
_hf_client = None
_hf_lock = threading.Lock()


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


def _get_huggingface_client():
    global _hf_client
    if _hf_client is not None:
        return _hf_client

    with _hf_lock:
        if _hf_client is None:
            settings = get_settings()
            api_key = settings.huggingface_api_key
            if not api_key:
                raise RuntimeError(
                    "HUGGINGFACE_API_KEY or HF_TOKEN is required when EMBEDDING_PROVIDER=huggingface"
                )
            from huggingface_hub import InferenceClient

            _hf_client = InferenceClient(token=api_key, timeout=90.0)
        return _hf_client


def _hf_error_retryable(exc: Exception) -> bool:
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status in {401, 403}:
        return False
    if status in {429, 503, 504}:
        return True
    if status is not None and status < 500:
        return False
    if isinstance(exc, (httpx.HTTPError, TimeoutError)):
        return True
    return exc.__class__.__name__ in {
        "HfHubHTTPError",
        "ReadTimeout",
        "ConnectTimeout",
    }


def _format_hf_embedding_error(exc: Exception) -> str:
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status == 401 or "401 Unauthorized" in str(exc):
        return (
            "HuggingFace embedding authentication failed (401). "
            "Set a valid HF_TOKEN on Railway with Inference Providers permission "
            "(https://huggingface.co/settings/tokens). "
            "Use only one HF_TOKEN variable — no empty duplicate entries."
        )
    if status == 403:
        return (
            "HuggingFace denied embedding access (403). "
            "Ensure your token has Inference Providers enabled for BAAI/bge-small-en-v1.5."
        )
    return f"HuggingFace embedding failed: {exc}"


def _encode_huggingface(texts: list[str], telemetry=None) -> list[list[float]]:
    settings = get_settings()
    client = _get_huggingface_client()
    api_batch = max(1, min(settings.EMBEDDING_BATCH_SIZE, 32))
    all_vectors: list[list[float]] = []

    import time

    for start in range(0, len(texts), api_batch):
        batch = texts[start : start + api_batch]
        batch_started = time.perf_counter()
        last_error: Exception | None = None

        for attempt in range(1, 4):
            try:
                result = client.feature_extraction(
                    batch,
                    model=settings.EMBEDDING_MODEL,
                )
                break
            except Exception as exc:
                if not _hf_error_retryable(exc):
                    logger.error("[EMBEDDING_AUTH_ERROR] %s", _format_hf_embedding_error(exc))
                    raise RuntimeError(_format_hf_embedding_error(exc)) from exc
                last_error = exc
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if telemetry:
                    telemetry.log(
                        "EMBEDDING_RETRY",
                        level=logging.WARNING,
                        attempt=attempt,
                        error=str(exc),
                        status_code=status,
                    )
                time.sleep(min(2 ** attempt, 8))
        else:
            raise RuntimeError(
                f"HuggingFace embedding failed after retries: {last_error}"
            ) from last_error

        elapsed = time.perf_counter() - batch_started
        if elapsed > 60:
            logger.warning(
                "HuggingFace embedding batch slow. Elapsed: %.1fs batch_size=%s",
                elapsed,
                len(batch),
            )

        import numpy as np

        array = np.asarray(result, dtype=float)
        if array.ndim == 1:
            batch_vectors = [array.tolist()]
        else:
            batch_vectors = array.tolist()

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


def encode_texts(
    texts: list[str],
    *,
    telemetry=None,
    batch_index: int | None = None,
    batch_total: int | None = None,
) -> list[list[float]]:
    if not texts:
        return []

    settings = get_settings()
    provider = settings.EMBEDDING_PROVIDER
    model_label = settings.embedding_model_label

    if telemetry:
        telemetry.log(
            "EMBEDDING_START",
            provider=provider,
            model=model_label,
            batch_index=batch_index,
            batch_total=batch_total,
            text_count=len(texts),
        )

    import time

    started = time.perf_counter()
    if provider == "openai":
        vectors = _encode_openai(texts)
    elif provider == "huggingface":
        vectors = _encode_huggingface(texts, telemetry=telemetry)
    else:
        vectors = _encode_local(texts)

    elapsed = time.perf_counter() - started
    if telemetry:
        telemetry.log(
            "EMBEDDING_COMPLETE",
            provider=provider,
            model=model_label,
            vector_count=len(vectors),
            duration_ms=round(elapsed * 1000, 1),
        )
    if elapsed > 60:
        logger.warning(
            "Embedding generation taking unusually long. Elapsed: %.1fs provider=%s model=%s count=%s",
            elapsed,
            provider,
            model_label,
            len(texts),
        )

    return vectors


def encode_query(text: str) -> list[float]:
    return encode_texts([text])[0]
