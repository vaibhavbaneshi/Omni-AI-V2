"""Tests for API vs local embedding routing."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.app_settings import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_encode_openai_uses_api(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    get_settings.cache_clear()

    mock_response = MagicMock()
    mock_response.data = [MagicMock(index=0, embedding=[0.1, 0.2, 0.3])]
    mock_client = MagicMock()
    mock_client.embeddings.create.return_value = mock_response

    with patch("app.services.embedding_service._get_openai_client", return_value=mock_client):
        from app.services.embedding_service import encode_texts

        vectors = encode_texts(["hello world"])

    assert vectors == [[0.1, 0.2, 0.3]]
    mock_client.embeddings.create.assert_called_once()


def test_encode_huggingface_uses_inference_api(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "huggingface")
    monkeypatch.setenv("HF_TOKEN", "hf_test")
    get_settings.cache_clear()

    mock_response = MagicMock()
    mock_response.json.return_value = [[3.0, 4.0]]
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    with patch("app.services.embedding_service.httpx.Client", return_value=mock_client):
        from app.services.embedding_service import encode_texts

        vectors = encode_texts(["hello"])

    assert len(vectors) == 1
    assert vectors[0][0] == pytest.approx(0.6)
    assert vectors[0][1] == pytest.approx(0.8)


def test_production_blocks_local_embeddings_without_flag(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("GROQ_API_KEY", "test")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "local")
    monkeypatch.setenv("ENABLE_LOCAL_ML", "false")
    get_settings.cache_clear()

    settings = get_settings()
    with pytest.raises(RuntimeError, match="EMBEDDING_PROVIDER=local is disabled"):
        settings.validate_for_runtime()
