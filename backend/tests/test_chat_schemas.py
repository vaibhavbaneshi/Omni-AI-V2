"""Tests for chat request schema resolution."""

import pytest
from fastapi import HTTPException
from starlette.requests import Request


def _build_request(
    *,
    content_type: str | None = None,
    query_string: str = "",
    body: bytes = b"",
) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if content_type:
        headers.append((b"content-type", content_type.encode("latin-1")))

    body_sent = False

    async def receive():
        nonlocal body_sent
        if body_sent:
            return {"type": "http.disconnect"}
        body_sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/chat-stream",
        "headers": headers,
        "query_string": query_string.encode("latin-1"),
    }
    return Request(scope, receive)


@pytest.mark.asyncio
async def test_resolve_chat_stream_request_empty_json_falls_back_to_query_params():
    from app.schemas.chat_schemas import resolve_chat_stream_request

    request = _build_request(
        content_type="application/json",
        query_string="query=hello&session_id=5&mode=research",
        body=b"",
    )
    resolved = await resolve_chat_stream_request(request)
    assert resolved.query == "hello"
    assert resolved.session_id == 5
    assert resolved.mode == "research"


@pytest.mark.asyncio
async def test_resolve_chat_stream_request_invalid_json_falls_back_to_query_params():
    from app.schemas.chat_schemas import resolve_chat_stream_request

    request = _build_request(
        content_type="application/json",
        query_string="query=hello&session_id=5&mode=research",
        body=b"not-json",
    )
    resolved = await resolve_chat_stream_request(request)
    assert resolved.query == "hello"
    assert resolved.session_id == 5


@pytest.mark.asyncio
async def test_resolve_chat_stream_request_json_body_takes_precedence():
    from app.schemas.chat_schemas import resolve_chat_stream_request

    request = _build_request(
        content_type="application/json",
        query_string="query=ignored&session_id=1&mode=research",
        body=b'{"query":"from-body","session_id":9,"mode":"research"}',
    )
    resolved = await resolve_chat_stream_request(request)
    assert resolved.query == "from-body"
    assert resolved.session_id == 9


@pytest.mark.asyncio
async def test_resolve_chat_stream_request_missing_query_params_returns_422():
    from app.schemas.chat_schemas import resolve_chat_stream_request

    request = _build_request(content_type="application/json", body=b"")
    with pytest.raises(HTTPException) as exc_info:
        await resolve_chat_stream_request(request)
    assert exc_info.value.status_code == 422
