from app.agent.orchestrator import AgentOrchestrator


def test_orchestrator_math_route():
    orchestrator = AgentOrchestrator()
    route = orchestrator.plan("calculate 12 * 8", mode="research")
    assert route.strategy == "calculator"
    assert "calculator" in route.tools
