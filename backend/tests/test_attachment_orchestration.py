from app.services.attachment_service import is_document_query, needs_calculator


def test_document_summary_does_not_route_to_calculator():
    from app.agent.orchestrator import AgentOrchestrator

    orchestrator = AgentOrchestrator()
    route = orchestrator.plan("summarize the attached PDF file", mode="research")
    assert route.strategy == "document-retrieval"
    assert "calculator" not in route.tools


def test_calculator_still_routes_for_math():
    from app.agent.orchestrator import AgentOrchestrator

    orchestrator = AgentOrchestrator()
    route = orchestrator.plan("calculate 12 * 8", mode="research")
    assert route.strategy == "calculator"


def test_summary_word_does_not_trigger_calculator():
    from app.agent.orchestrator import AgentOrchestrator

    orchestrator = AgentOrchestrator()
    route = orchestrator.plan("give me a summary of our conversation", mode="research")
    assert route.strategy != "calculator"


def test_is_document_query():
    assert is_document_query("summarize this PDF")
    assert is_document_query("what is in the uploaded document")
    assert not is_document_query("hello there")


def test_needs_calculator_excludes_document_queries():
    assert not needs_calculator("summarize attached file")
    assert needs_calculator("calculate 15 percent of 240")
