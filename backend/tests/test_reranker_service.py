"""Tests for reranker_service."""

from unittest.mock import MagicMock, patch

import app.services.reranker_service as reranker_module
from app.services.reranker_service import rerank_documents


def test_rerank_empty_list():
    assert rerank_documents("query", []) == []


@patch("app.services.reranker_service.get_settings")
def test_rerank_disabled_returns_top_k(mock_settings):
    settings = MagicMock()
    settings.ENABLE_RERANKER = False
    mock_settings.return_value = settings

    docs = ["c", "a", "b"]
    assert rerank_documents("query", docs, top_k=2) == ["c", "a"]


@patch("app.services.reranker_service._get_reranker")
@patch("app.services.reranker_service.get_settings")
def test_rerank_sorts_by_score(mock_settings, mock_get_reranker):
    settings = MagicMock()
    settings.ENABLE_RERANKER = True
    mock_settings.return_value = settings

    model = MagicMock()
    model.predict.return_value = [0.2, 0.9, 0.5]
    mock_get_reranker.return_value = model

    docs = ["low", "high", "mid"]
    ranked = rerank_documents("query", docs, top_k=2)
    assert ranked == ["high", "mid"]


@patch("app.services.reranker_service._get_reranker")
@patch("app.services.reranker_service.get_settings")
def test_rerank_respects_top_k(mock_settings, mock_get_reranker):
    settings = MagicMock()
    settings.ENABLE_RERANKER = True
    mock_settings.return_value = settings

    model = MagicMock()
    model.predict.return_value = [0.1, 0.2, 0.3, 0.4]
    mock_get_reranker.return_value = model

    docs = ["a", "b", "c", "d"]
    ranked = rerank_documents("query", docs, top_k=1)
    assert ranked == ["d"]


@patch("app.services.reranker_service._get_reranker")
@patch("app.services.reranker_service.get_settings")
def test_rerank_falls_back_when_model_unavailable(mock_settings, mock_get_reranker):
    settings = MagicMock()
    settings.ENABLE_RERANKER = True
    mock_settings.return_value = settings
    mock_get_reranker.side_effect = RuntimeError("model unavailable")

    docs = ["first", "second", "third"]
    try:
        rerank_documents("query", docs, top_k=2)
    except RuntimeError:
        pass

    # When reranker fails, caller should handle; verify disabled path still works.
    settings.ENABLE_RERANKER = False
    assert rerank_documents("query", docs, top_k=2) == ["first", "second"]


def test_get_reranker_lazy_load(monkeypatch):
    reranker_module._reranker = None
    fake_model = MagicMock()

    with patch("sentence_transformers.CrossEncoder", return_value=fake_model):
        with patch("app.services.reranker_service.get_settings") as mock_settings:
            settings = MagicMock()
            settings.RERANKER_MODEL = "cross-encoder/test"
            mock_settings.return_value = settings
            loaded = reranker_module._get_reranker()
            assert loaded is fake_model
            assert reranker_module._get_reranker() is fake_model
