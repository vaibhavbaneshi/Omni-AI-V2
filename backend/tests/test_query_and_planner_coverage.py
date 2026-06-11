"""Coverage for query contextualizer and research planner."""

from unittest.mock import patch

from app.research.planner import plan_research
from app.services.query_contextualizer_service import (
    contextualize_query,
    needs_contextualization,
    resolve_retrieval_query,
)


def test_needs_contextualization_detects_followups():
    history = "user: Explain vector databases\nassistant: They store embeddings."
    assert needs_contextualization("Tell me more about that", history)
    assert not needs_contextualization("What is PostgreSQL?", "")


def test_contextualize_query_heuristic_when_disabled(monkeypatch):
    monkeypatch.setenv("ENABLE_QUERY_REWRITING", "false")
    from app.core.app_settings import get_settings

    get_settings.cache_clear()
    history = "user: Explain vector databases\nassistant: They store embeddings."
    rewritten = contextualize_query("Expand on that", history=history)
    assert "context of" in rewritten
    get_settings.cache_clear()


@patch("app.services.query_contextualizer_service.invoke_generate", return_value="Standalone vector database question")
def test_contextualize_query_llm(mock_invoke, monkeypatch):
    monkeypatch.setenv("ENABLE_QUERY_REWRITING", "true")
    from app.core.app_settings import get_settings

    get_settings.cache_clear()
    history = "user: Explain vector databases\nassistant: They store embeddings."
    rewritten = contextualize_query("Expand on that", history=history)
    assert "Standalone" in rewritten
    get_settings.cache_clear()


@patch("app.services.query_contextualizer_service.invoke_generate", side_effect=RuntimeError("llm down"))
def test_contextualize_query_fallback_on_error(mock_invoke, monkeypatch):
    monkeypatch.setenv("ENABLE_QUERY_REWRITING", "true")
    from app.core.app_settings import get_settings

    get_settings.cache_clear()
    history = "user: Explain vector databases\nassistant: They store embeddings."
    rewritten = contextualize_query("Expand on that", history=history)
    assert "context of" in rewritten
    get_settings.cache_clear()


def test_resolve_retrieval_query_returns_original_when_unchanged():
    query, original = resolve_retrieval_query("What is RAG?", history="")
    assert query == "What is RAG?"
    assert original is None


@patch("app.services.query_contextualizer_service.contextualize_query", return_value="Rewritten standalone query")
def test_resolve_retrieval_query_returns_original_when_rewritten(mock_context):
    query, original = resolve_retrieval_query("Tell me more", history="user: hi")
    assert query == "Rewritten standalone query"
    assert original == "Tell me more"


@patch("app.research.planner.invoke_generate", return_value='{"goal": "Study RAG", "sub_problems": ["What is RAG?"], "search_queries": ["RAG systems"]}')
def test_plan_research(mock_invoke):
    plan = plan_research("What is RAG?")
    assert plan["goal"] == "Study RAG"
    assert plan["search_queries"]


@patch("app.research.planner.invoke_generate", return_value="not-json")
def test_plan_research_fallback(mock_invoke):
    plan = plan_research("What is RAG?")
    assert plan["goal"] == "What is RAG?"
