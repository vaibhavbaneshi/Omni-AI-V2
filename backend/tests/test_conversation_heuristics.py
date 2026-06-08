from app.agent.orchestrator import AgentOrchestrator
from app.services.conversation_heuristics import is_simple_conversational_query
from app.services.prompt_builder import build_stream_prompt


def test_simple_greetings_are_conversational():
    assert is_simple_conversational_query("hi")
    assert is_simple_conversational_query("hello!")
    assert is_simple_conversational_query("now")
    assert is_simple_conversational_query("thanks")


def test_research_queries_are_not_conversational():
    assert not is_simple_conversational_query("what is machine learning?")
    assert not is_simple_conversational_query("summarize this document")
    assert not is_simple_conversational_query("help me write python code")


def test_orchestrator_skips_web_search_for_hi():
    route = AgentOrchestrator().plan(query="hi", mode="research")
    assert route.strategy == "direct-chat"
    assert route.tools == []


def test_stream_prompt_for_hi_is_concise():
    prompt = build_stream_prompt(query="hi")
    assert "1-2 short sentences" in prompt
    assert "# Summary" not in prompt
