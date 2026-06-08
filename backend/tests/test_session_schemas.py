"""Tests for session request schema resolution."""

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
        "path": "/sessions",
        "headers": headers,
        "query_string": query_string.encode("latin-1"),
    }
    return Request(scope, receive)


@pytest.mark.asyncio
async def test_resolve_create_session_request_json_body():
    from app.schemas.session_schemas import resolve_create_session_request

    request = _build_request(
        content_type="application/json",
        body=b'{"title":"Planning","first_message":"hello there"}',
    )
    resolved = await resolve_create_session_request(request)
    assert resolved.title == "Planning"
    assert resolved.first_message == "hello there"


@pytest.mark.asyncio
async def test_resolve_create_session_request_empty_json_falls_back_to_query():
    from app.schemas.session_schemas import resolve_create_session_request

    request = _build_request(
        content_type="application/json",
        query_string="title=New+Chat&first_message=hi",
        body=b"",
    )
    resolved = await resolve_create_session_request(request)
    assert resolved.title == "New Chat"
    assert resolved.first_message == "hi"


@pytest.mark.asyncio
async def test_resolve_create_session_request_query_only():
    from app.schemas.session_schemas import resolve_create_session_request

    request = _build_request(query_string="title=Draft&first_message=plan")
    resolved = await resolve_create_session_request(request)
    assert resolved.title == "Draft"
    assert resolved.first_message == "plan"


@pytest.mark.asyncio
async def test_resolve_create_session_request_rejects_empty_title():
    from app.schemas.session_schemas import resolve_create_session_request

    request = _build_request(
        content_type="application/json",
        body=b'{"title":"","first_message":"hi"}',
    )
    with pytest.raises(HTTPException) as exc_info:
        await resolve_create_session_request(request)
    assert exc_info.value.status_code == 422
