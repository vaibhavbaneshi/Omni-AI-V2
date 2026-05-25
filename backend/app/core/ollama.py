"""Resolve Ollama API endpoints and model names from environment configuration."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


def resolve_ollama_generate_url(url: str | None) -> str:
    """
    Normalize OLLAMA_URL to Ollama's /api/generate endpoint.

    Common misconfiguration: http://localhost:11434/ (returns 405 on POST).
    """
    if not url or not str(url).strip():
        return ""

    base = str(url).strip().rstrip("/")

    if base.endswith("/api/generate"):
        return base

    # This codebase uses the /api/generate payload shape (prompt + response).
    if base.endswith("/api/chat"):
        return f"{base.rsplit('/api/chat', 1)[0]}/api/generate"

    if "/api/" in base:
        return base

    return f"{base}/api/generate"


def ollama_base_url(generate_url: str) -> str:
    parsed = urlparse(generate_url)
    return f"{parsed.scheme}://{parsed.netloc}"


def list_installed_ollama_models(generate_url: str, timeout: int = 5) -> list[str]:
    if not generate_url:
        return []

    tags_url = f"{ollama_base_url(generate_url)}/api/tags"

    try:
        response = requests.get(tags_url, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        logger.warning("Could not list Ollama models from %s: %s", tags_url, exc)
        return []

    models: list[str] = []
    for entry in payload.get("models", []):
        name = entry.get("name") if isinstance(entry, dict) else None
        if name:
            models.append(name)

    return models


def resolve_ollama_model_name(
    requested: str | None,
    generate_url: str,
    *,
    timeout: int = 5,
) -> str:
    """
    Return a model name that exists in the local Ollama instance.

    Ollama returns HTTP 404 on /api/generate when the model is missing.
    """
    installed = list_installed_ollama_models(generate_url, timeout=timeout)
    requested = (requested or "").strip()

    if not installed:
        if requested:
            return requested
        raise RuntimeError(
            "No Ollama models are installed. Run `ollama pull llama3` (or another model) "
            "and set MODEL_NAME in backend/.env to match `ollama list`."
        )

    if requested:
        if requested in installed:
            return requested

        requested_base = requested.split(":")[0]
        for name in installed:
            if name == requested_base or name.split(":")[0] == requested_base:
                logger.info(
                    "Resolved MODEL_NAME %s to installed model %s",
                    requested,
                    name,
                )
                return name

    fallback = installed[0]
    if requested:
        logger.warning(
            "MODEL_NAME %s is not installed. Using %s instead. Available: %s",
            requested,
            fallback,
            ", ".join(installed),
        )
    return fallback


def raise_ollama_http_error(exc: requests.HTTPError, *, generate_url: str, model: str) -> None:
    response = exc.response
    status = response.status_code if response is not None else None
    detail = ""

    if response is not None:
        try:
            body: Any = response.json()
            detail = body.get("error", "") if isinstance(body, dict) else ""
        except Exception:
            detail = (response.text or "").strip()

    installed = list_installed_ollama_models(generate_url)

    if status == 404:
        hint = (
            f"Model '{model}' was not found in Ollama. "
            f"Installed models: {', '.join(installed) if installed else '(none)'}. "
            "Update MODEL_NAME in backend/.env to match `ollama list`, "
            "or run `ollama pull <model>`."
        )
        raise RuntimeError(hint) from exc

    message = f"Failed to contact model server at {generate_url}: {exc}"
    if detail:
        message = f"{message} — {detail}"
    raise RuntimeError(message) from exc
