"""Integration tests — streaming chat endpoint."""

from unittest.mock import patch

from tests.factories import ChatSessionFactory


def _agent_payload(**overrides):
    payload = {
        "context": "Refund policy context",
        "sources": [],
        "tool": "rag",
        "strategy": "hybrid-rerank",
        "route": {"strategy": "web-rag-hybrid"},
        "source_groups": {},
        "tools": [],
        "traces": [],
        "mode": "research",
    }
    payload.update(overrides)
    return payload


@patch("app.api.chat_routes.should_refine_session_title", return_value=False)
@patch("app.api.chat_routes.generate_summary")
@patch("app.api.chat_routes.summarize_conversation", return_value="")
@patch("app.api.chat_routes.stream_response")
@patch("app.api.chat_routes.tool_calling_agent")
def test_chat_stream_returns_ndjson_tokens(
    mock_agent,
    mock_stream,
    _mock_summary,
    _mock_generate_summary,
    _mock_should_refine,
    auth_client,
    db_session,
):
    session = ChatSessionFactory(user=auth_client.auth_user, title="Stream Chat")
    mock_agent.return_value = _agent_payload()
    mock_stream.return_value = iter(["Hello", " world"])

    response = auth_client.post(
        f"/chat-stream?query=What+is+the+refund+policy&session_id={session.id}&mode=research",
        headers=auth_client.auth_headers,
    )

    assert response.status_code == 200
    lines = [line for line in response.text.split("\n") if line.strip()]
    event_types = [__import__("json").loads(line)["type"] for line in lines]
    assert "status" in event_types
    assert "meta" in event_types
    assert "token" in event_types
    assert event_types[-1] == "done"
    token_content = "".join(
        __import__("json").loads(line)["content"]
        for line in lines
        if __import__("json").loads(line).get("type") == "token"
    )
    assert token_content == "Hello world"


@patch("app.api.chat_routes.summarize_conversation", return_value="")
@patch("app.api.chat_routes.tool_calling_agent")
def test_chat_stream_session_not_found(mock_agent, _mock_summary, auth_client):
    mock_agent.return_value = _agent_payload()

    response = auth_client.post(
        "/chat-stream?query=hello&session_id=99999&mode=research",
        headers=auth_client.auth_headers,
    )
    assert response.status_code == 404


def test_legacy_chat_endpoint(auth_client, db_session):
    session = ChatSessionFactory(user=auth_client.auth_user, title="Legacy Chat")

    with patch("app.api.chat_routes.chat_with_rag") as mock_rag:
        with patch("app.api.chat_routes.generate_summary"):
            mock_rag.return_value = {"response": "Legacy answer", "context": "", "query": "hi"}
            response = auth_client.post(
                f"/chat?query=hello&session_id={session.id}",
                headers=auth_client.auth_headers,
            )

    assert response.status_code == 200
    assert response.json()["response"] == "Legacy answer"
