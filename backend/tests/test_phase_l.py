"""Phase L tests — OAuth cookies, upload security, cache, RBAC, audit."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.cookie_auth import ACCESS_COOKIE, CSRF_COOKIE, CSRF_HEADER, generate_csrf_token, set_auth_cookies
from app.services.redis_cache_service import cache_metrics, cache_retrieval_result, get_retrieval_cache
from app.services.upload_security_service import UploadSecurityError, validate_extension
from tests.factories import UserFactory


def test_validate_extension_blocks_executables():
    with pytest.raises(UploadSecurityError):
        validate_extension("malware.exe")


def test_redis_cache_hit_miss():
    cache_retrieval_result(
        query="hello",
        user_id=1,
        workspace_id="default",
        collection_id=None,
        session_id=1,
        value="context",
    )
    assert get_retrieval_cache(
        query="hello",
        user_id=1,
        workspace_id="default",
        collection_id=None,
        session_id=1,
    ) == "context"
    metrics = cache_metrics()
    assert metrics["hits"] >= 1


def test_set_auth_cookies(client: TestClient):
    from fastapi import Response

    response = Response()
    csrf = set_auth_cookies(response, access_token="access", refresh_token="refresh")
    assert csrf
    cookie_header = response.headers.get("set-cookie", "")
    assert ACCESS_COOKIE in cookie_header


@patch("app.core.rbac.user_has_admin_access", return_value=True)
def test_audit_overview_requires_admin(_mock, client: TestClient, auth_headers):
    response = client.get("/audit/overview", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "uploads" in body
    assert "security_events" in body


@patch("app.core.rbac.user_has_admin_access", return_value=True)
def test_audit_users_list(_mock, client: TestClient, auth_headers, db_session):
    user = UserFactory()
    response = client.get("/audit/users", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_auth_session_endpoint(client: TestClient, auth_headers):
    response = client.get("/auth/session", headers=auth_headers)
    assert response.status_code == 200
    assert "email" in response.json()
