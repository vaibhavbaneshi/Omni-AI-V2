"""Unified LLM provider abstraction (Groq production, OpenAI/Ollama optional)."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any, Iterator

import requests

from app.core.app_settings import get_settings
from app.core.ollama import (
    raise_ollama_http_error,
    resolve_ollama_generate_url,
    resolve_ollama_model_name,
)

logger = logging.getLogger(__name__)


class LLMProviderError(RuntimeError):
    """Raised when an LLM provider request fails."""


class BaseLLMProvider(ABC):
    name: str

    @property
    @abstractmethod
    def model_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.35,
        timeout: int = 120,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def stream_generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.35,
        timeout: int = 120,
    ) -> Iterator[str]:
        raise NotImplementedError

    def health_check(self, *, probe_network: bool = False) -> dict[str, Any]:
        return {
            "status": "ok",
            "provider": self.name,
            "model": self.model_name,
        }


class GroqProvider(BaseLLMProvider):
    name = "groq"

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.GROQ_API_KEY.strip()
        self._model = settings.GROQ_MODEL.strip() or "llama-3.3-70b-versatile"
        self._client = None

    @property
    def model_name(self) -> str:
        return self._model

    def _get_client(self):
        if not self._api_key:
            raise LLMProviderError(
                "GROQ_API_KEY is not configured. Set it in environment variables."
            )
        if self._client is None:
            try:
                from groq import Groq
            except ImportError as exc:
                raise LLMProviderError(
                    "Groq SDK is not installed. Add `groq` to requirements.txt."
                ) from exc
            self._client = Groq(api_key=self._api_key)
        return self._client

    def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.35,
        timeout: int = 120,
    ) -> str:
        client = self._get_client()
        try:
            completion = client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                timeout=timeout,
            )
        except Exception as exc:
            raise LLMProviderError(f"Groq generation failed: {exc}") from exc

        message = completion.choices[0].message
        return (message.content or "").strip()

    def stream_generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.35,
        timeout: int = 120,
    ) -> Iterator[str]:
        client = self._get_client()
        try:
            stream = client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                stream=True,
                timeout=timeout,
            )
        except Exception as exc:
            raise LLMProviderError(f"Groq streaming failed: {exc}") from exc

        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta

    def health_check(self, *, probe_network: bool = False) -> dict[str, Any]:
        if not self._api_key:
            return {
                "status": "warning",
                "provider": self.name,
                "detail": "GROQ_API_KEY is not configured",
            }
        if not probe_network:
            return {
                "status": "ok",
                "provider": self.name,
                "model": self._model,
                "configured": True,
            }
        try:
            self.generate("Reply with OK.", temperature=0.0, timeout=15)
            return {"status": "ok", "provider": self.name, "model": self._model}
        except Exception as exc:
            return {
                "status": "warning",
                "provider": self.name,
                "detail": str(exc),
            }


class OpenAIProvider(BaseLLMProvider):
    name = "openai"

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.OPENAI_API_KEY.strip()
        self._model = settings.OPENAI_MODEL.strip() or "gpt-4o-mini"
        self._client = None

    @property
    def model_name(self) -> str:
        return self._model

    def _get_client(self):
        if not self._api_key:
            raise LLMProviderError(
                "OPENAI_API_KEY is not configured. Set it in environment variables."
            )
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise LLMProviderError(
                    "OpenAI SDK is not installed. Add `openai` to requirements.txt."
                ) from exc
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.35,
        timeout: int = 120,
    ) -> str:
        client = self._get_client()
        try:
            completion = client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                timeout=timeout,
            )
        except Exception as exc:
            raise LLMProviderError(f"OpenAI generation failed: {exc}") from exc

        message = completion.choices[0].message
        return (message.content or "").strip()

    def stream_generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.35,
        timeout: int = 120,
    ) -> Iterator[str]:
        client = self._get_client()
        try:
            stream = client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                stream=True,
                timeout=timeout,
            )
        except Exception as exc:
            raise LLMProviderError(f"OpenAI streaming failed: {exc}") from exc

        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta

    def health_check(self, *, probe_network: bool = False) -> dict[str, Any]:
        if not self._api_key:
            return {
                "status": "warning",
                "provider": self.name,
                "detail": "OPENAI_API_KEY is not configured",
            }
        if not probe_network:
            return {
                "status": "ok",
                "provider": self.name,
                "model": self._model,
                "configured": True,
            }
        try:
            self.generate("Reply with OK.", temperature=0.0, timeout=15)
            return {"status": "ok", "provider": self.name, "model": self._model}
        except Exception as exc:
            return {
                "status": "warning",
                "provider": self.name,
                "detail": str(exc),
            }


class OllamaProvider(BaseLLMProvider):
    name = "ollama"

    def __init__(self) -> None:
        settings = get_settings()
        self._generate_url = resolve_ollama_generate_url(settings.OLLAMA_URL)
        self._requested_model = settings.MODEL_NAME
        self._resolved_model: str | None = None

    @property
    def model_name(self) -> str:
        # Never contact Ollama for model discovery outside inference.
        return self._resolved_model or self._requested_model

    def _resolve_model_for_inference(self) -> str:
        if self._resolved_model:
            return self._resolved_model
        if not self._generate_url:
            raise LLMProviderError(
                "OLLAMA_URL is not configured. Set OLLAMA_URL for local Ollama usage."
            )
        try:
            self._resolved_model = resolve_ollama_model_name(
                self._requested_model,
                self._generate_url,
            )
        except RuntimeError:
            self._resolved_model = self._requested_model or "llama3:latest"
        return self._resolved_model

    def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.35,
        timeout: int = 120,
    ) -> str:
        model = self._resolve_model_for_inference()
        try:
            response = requests.post(
                self._generate_url,
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": temperature},
                },
                timeout=timeout,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise_ollama_http_error(exc, generate_url=self._generate_url, model=model)
        except requests.RequestException as exc:
            raise LLMProviderError(
                f"Failed to contact Ollama at {self._generate_url}: {exc}"
            ) from exc

        data = response.json()
        return data.get("response", "")

    def stream_generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.35,
        timeout: int = 120,
    ) -> Iterator[str]:
        model = self._resolve_model_for_inference()
        try:
            response = requests.post(
                self._generate_url,
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {"temperature": temperature},
                },
                stream=True,
                timeout=timeout,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise_ollama_http_error(exc, generate_url=self._generate_url, model=model)
        except requests.RequestException as exc:
            raise LLMProviderError(
                f"Failed to contact Ollama at {self._generate_url}: {exc}"
            ) from exc

        for line in response.iter_lines():
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                logger.debug("Skipping malformed Ollama stream line")
                continue
            token = data.get("response", "")
            if token:
                yield token

    def health_check(self, *, probe_network: bool = False) -> dict[str, Any]:
        if not self._generate_url:
            return {
                "status": "warning",
                "provider": self.name,
                "detail": "OLLAMA_URL is not configured",
            }
        if not probe_network:
            return {
                "status": "ok",
                "provider": self.name,
                "model": self._requested_model,
                "configured": True,
            }
        try:
            model = self._resolve_model_for_inference()
            return {"status": "ok", "provider": self.name, "model": model}
        except Exception as exc:
            return {
                "status": "warning",
                "provider": self.name,
                "detail": str(exc),
            }


@lru_cache
def get_llm_provider() -> BaseLLMProvider:
    settings = get_settings()
    provider = (settings.LLM_PROVIDER or "groq").strip().lower()
    if provider == "groq":
        return GroqProvider()
    if provider == "openai":
        return OpenAIProvider()
    if provider == "ollama":
        return OllamaProvider()
    raise LLMProviderError(
        f"Unsupported LLM_PROVIDER '{settings.LLM_PROVIDER}'. Use 'groq', 'openai', or 'ollama'."
    )


def get_llm() -> BaseLLMProvider:
    """Return the configured LLM provider instance."""
    return get_llm_provider()


def reset_llm_provider_cache() -> None:
    get_llm_provider.cache_clear()
