"""Phase L completion tests — upload security, GitHub connector, audit, cookies, CSRF, cache."""

from __future__ import annotations

import base64
import zipfile
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Response
from starlette.requests import Request

from app.core.cookie_auth import (
    ACCESS_COOKIE,
    CSRF_COOKIE,
    CSRF_HEADER,
    clear_auth_cookies,
    generate_csrf_token,
    get_access_token_from_request,
    get_refresh_token_from_request,
    set_auth_cookies,
    validate_csrf,
)
from app.middleware.csrf import CSRFMiddleware
from app.models.agent_trace import AgentTrace
from app.models.document import DocumentRecord
from app.models.github_connector import GitHubConnection, GitHubRepositorySync
from app.models.rbac import UserRole
from app.models.research_report import ResearchReport
from app.services.audit_service import (
    export_audit_events_csv,
    get_audit_overview,
    list_audit_events,
    list_users_with_roles,
)
from app.services.file_scanner import FileScanError, scan_uploaded_file
from app.services.github_connector_service import (
    _decode_content,
    build_connector_authorize_url,
    get_connection,
    handle_connector_callback,
    list_repositories,
    save_connection,
    sync_repository,
)
from app.services.redis_cache_service import (
    cache_embedding,
    cache_query_result,
    get_embedding_cache,
    get_query_cache,
)
from app.services.upload_security_service import (
    UploadSecurityError,
    check_pdf_sanity,
    check_zip_bomb,
    process_upload_security,
    quarantine_directory,
    scan_with_clamav,
    validate_extension,
    validate_mime,
)
from app.services.workspace_connector_service import get_connector, list_connectors, sync_connector
from tests.factories import UserFactory


def test_validate_extension_allowlist_and_blocks():
    validate_extension("notes.pdf")
    validate_extension("readme.md")
    with pytest.raises(UploadSecurityError):
        validate_extension("script.exe")
    with pytest.raises(UploadSecurityError):
        validate_extension("archive.rar")


def test_validate_mime_blocks_javascript():
    validate_mime("text/plain")
    with pytest.raises(UploadSecurityError):
        validate_mime("application/javascript")


def test_check_zip_bomb_rejects_large_archives(tmp_path):
    archive_path = tmp_path / "big.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("a.txt", "x" * 1024)
        archive.writestr("../escape.txt", "bad")
    with pytest.raises(UploadSecurityError, match="unsafe paths"):
        check_zip_bomb(str(archive_path))


def test_check_zip_bomb_rejects_invalid_archive(tmp_path):
    bad_path = tmp_path / "bad.zip"
    bad_path.write_bytes(b"not-a-zip")
    with pytest.raises(UploadSecurityError, match="Invalid ZIP"):
        check_zip_bomb(str(bad_path))


def test_check_pdf_sanity_rejects_javascript(tmp_path):
    pdf_path = tmp_path / "evil.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n/JavaScript alert(1)")
    with pytest.raises(UploadSecurityError, match="JavaScript"):
        check_pdf_sanity(str(pdf_path))


def test_scan_with_clamav_skips_when_disabled(monkeypatch, tmp_path):
    sample = tmp_path / "clean.txt"
    sample.write_text("hello")
    monkeypatch.setenv("CLAMAV_ENABLED", "false")
    from app.core.app_settings import get_settings

    get_settings.cache_clear()
    scan_with_clamav(str(sample))
    get_settings.cache_clear()


def test_scan_with_clamav_detects_malware(monkeypatch, tmp_path):
    sample = tmp_path / "infected.txt"
    sample.write_text("payload")
    monkeypatch.setenv("CLAMAV_ENABLED", "true")
    monkeypatch.setenv("CLAMAV_REQUIRED", "true")
    from app.core.app_settings import get_settings

    get_settings.cache_clear()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="Eicar FOUND", stderr="")
        with pytest.raises(UploadSecurityError, match="Malware"):
            scan_with_clamav(str(sample))
    get_settings.cache_clear()


def test_process_upload_security_approves_clean_file(tmp_path):
    file_path = tmp_path / "notes.txt"
    file_path.write_text("safe content")
    approved = process_upload_security(
        quarantine_path=str(file_path),
        filename="notes.txt",
        content_type="text/plain",
        user_id=1,
    )
    assert approved == str(file_path)


def test_file_scanner_wraps_upload_security_errors(tmp_path):
    file_path = tmp_path / "bad.exe"
    file_path.write_bytes(b"MZ")
    with pytest.raises(FileScanError):
        scan_uploaded_file(str(file_path), filename="bad.exe", user_id=1)


def test_quarantine_directory_creates_user_path(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_STAGING_DIR", str(tmp_path))
    from app.core.app_settings import get_settings

    get_settings.cache_clear()
    path = quarantine_directory(user_id=7, session_id=3)
    assert path.endswith("7/3")
    assert tmp_path.joinpath("7", "3").is_dir()
    get_settings.cache_clear()


def test_cookie_auth_helpers():
    csrf = generate_csrf_token()
    assert len(csrf) > 20

    response = Response()
    returned = set_auth_cookies(response, access_token="a", refresh_token="r", csrf_token=csrf)
    assert returned == csrf
    clear_auth_cookies(response)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"authorization", b"Bearer legacy-token")],
    }
    request = Request(scope)
    assert get_access_token_from_request(request) == "legacy-token"

    scope["headers"] = [(b"cookie", f"{ACCESS_COOKIE}=cookie-token".encode())]
    request = Request(scope)
    assert get_access_token_from_request(request) == "cookie-token"
    assert get_refresh_token_from_request(request) is None


def test_validate_csrf_compares_cookie_and_header():
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [
            (b"cookie", f"{CSRF_COOKIE}=abc123".encode()),
            (CSRF_HEADER.lower().encode(), b"abc123"),
        ],
    }
    request = Request(scope)
    assert validate_csrf(request) is True

    scope["headers"] = [
        (b"cookie", f"{CSRF_COOKIE}=abc123".encode()),
        (CSRF_HEADER.lower().encode(), b"wrong"),
    ]
    request = Request(scope)
    assert validate_csrf(request) is False


@pytest.mark.asyncio
async def test_csrf_middleware_blocks_missing_token():
    middleware = CSRFMiddleware(app=MagicMock())

    async def call_next(request):
        return Response(status_code=200)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/sessions",
        "headers": [(b"cookie", f"{ACCESS_COOKIE}=token".encode())],
    }
    request = Request(scope)
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 403


def test_audit_service_overview_and_export(db_session):
    user = UserFactory()
    from app.models.document import DocumentCollection

    collection = DocumentCollection(user_id=user.id, workspace_id="default", name="Uploads")
    db_session.add(collection)
    db_session.flush()
    db_session.add(
        DocumentRecord(
            user_id=user.id,
            collection_id=collection.id,
            workspace_id="default",
            filename="report.pdf",
            storage_path="/tmp/report.pdf",
            file_size=100,
            security_status="approved",
            indexing_stage="complete",
        )
    )
    from app.services.security_audit_service import audit_log

    audit_log(
        db_session,
        action="upload.rejected",
        user_id=user.id,
        ip_address="127.0.0.1",
        detail={"reason": "blocked extension"},
    )
    db_session.add(
        AgentTrace(
            user_id=user.id,
            session_id=1,
            query="test query",
            status="complete",
            latency_ms=120,
        )
    )
    db_session.add(
        ResearchReport(
            user_id=user.id,
            query="research topic",
            status="ready",
            report={"markdown": "# Report"},
        )
    )
    db_session.add(UserRole(user_id=user.id, role="admin"))
    db_session.commit()

    overview = get_audit_overview(db_session, days=30)
    assert overview["uploads"]["total"] >= 1
    assert overview["agent_traces"]["complete"] >= 1
    assert overview["research_reports"]["ready"] >= 1
    assert overview["rbac"]["assignments"] >= 1

    events = list_audit_events(db_session, action_prefix="upload", limit=10)
    assert events["total"] >= 1

    csv_data = export_audit_events_csv(db_session)
    assert "upload.rejected" in csv_data

    users = list_users_with_roles(db_session)
    assert users["total"] >= 1
    assert any(row["email"] == user.email for row in users["users"])


def test_github_save_and_get_connection(db_session):
    user = UserFactory()
    record = save_connection(
        db_session,
        user_id=user.id,
        github_user_id="123",
        github_login="octocat",
        access_token="gh-token",
    )
    assert record.id is not None
    assert get_connection(db_session, user_id=user.id).github_login == "octocat"

    updated = save_connection(
        db_session,
        user_id=user.id,
        github_user_id="123",
        github_login="octocat2",
        access_token="gh-token-2",
    )
    assert updated.id == record.id
    assert updated.github_login == "octocat2"


def test_github_build_authorize_url():
    with patch("app.services.github_connector_service.get_oauth_settings") as mock_settings:
        mock_settings.return_value = {
            "github_client_id": "client-id",
            "api_public_url": "http://localhost:8000",
        }
        url = build_connector_authorize_url(next_path="/dashboard")
    assert "github.com/login/oauth/authorize" in url
    assert "client_id=client-id" in url


def test_github_handle_connector_callback(db_session):
    user = UserFactory()
    with patch("app.services.github_connector_service.decode_oauth_state"):
        with patch("app.services.github_connector_service.exchange_github_code", return_value="tok"):
            with patch(
                "app.services.github_connector_service._github_get",
                return_value={"id": 99, "login": "devuser"},
            ):
                connection = handle_connector_callback(
                    db_session,
                    user=user,
                    code="code",
                    state="state",
                )
    assert connection.github_login == "devuser"
    assert connection.access_token == "tok"


def test_github_list_repositories(db_session):
    user = UserFactory()
    save_connection(
        db_session,
        user_id=user.id,
        github_user_id="1",
        github_login="dev",
        access_token="token",
    )
    db_session.add(
        GitHubRepositorySync(
            user_id=user.id,
            connection_id=get_connection(db_session, user_id=user.id).id,
            repo_full_name="org/repo",
            default_branch="main",
            workspace_id="default",
            sync_status="complete",
            last_sync_at=datetime.utcnow(),
        )
    )
    db_session.commit()

    with patch(
        "app.services.github_connector_service._github_get",
        return_value=[
            {
                "full_name": "org/repo",
                "private": False,
                "default_branch": "main",
                "description": "Demo",
            }
        ],
    ):
        repos = list_repositories(db_session, user_id=user.id)
    assert repos[0]["sync_status"] == "complete"
    assert repos[0]["last_sync_at"] is not None


@patch("app.services.ingestion_service.run_ingest_document_record")
def test_github_sync_repository_indexes_files(mock_ingest, db_session):
    user = UserFactory()
    connection = save_connection(
        db_session,
        user_id=user.id,
        github_user_id="1",
        github_login="dev",
        access_token="token",
    )

    commit_sha = "abc123"
    encoded = base64.b64encode(b"# Hello\n").decode()

    def fake_github_get(token, path, params=None):
        if path == "/repos/acme/docs":
            return {"default_branch": "main"}
        if "/commits/" in path:
            return {"sha": commit_sha}
        if "/git/trees/" in path:
            return {
                "tree": [
                    {"type": "blob", "path": "README.md", "size": 20},
                    {"type": "tree", "path": "src", "size": 0},
                ]
            }
        if path.endswith("/contents/README.md"):
            return {"encoding": "base64", "content": encoded}
        raise AssertionError(f"Unexpected path: {path}")

    with patch("app.services.github_connector_service._github_get", side_effect=fake_github_get):
        result = sync_repository(
            db_session,
            user=user,
            repo_full_name="acme/docs",
            workspace_id="default",
        )
    assert result["status"] == "complete"
    assert result["files_indexed"] == 1
    mock_ingest.assert_called_once()


def test_github_sync_repository_returns_unchanged(db_session):
    user = UserFactory()
    connection = save_connection(
        db_session,
        user_id=user.id,
        github_user_id="1",
        github_login="dev",
        access_token="token",
    )
    db_session.add(
        GitHubRepositorySync(
            user_id=user.id,
            connection_id=connection.id,
            repo_full_name="acme/docs",
            default_branch="main",
            workspace_id="default",
            sync_status="complete",
            last_commit_sha="same-sha",
            files_indexed=3,
        )
    )
    db_session.commit()

    with patch(
        "app.services.github_connector_service._github_get",
        side_effect=[
            {"default_branch": "main"},
            {"sha": "same-sha"},
        ],
    ):
        result = sync_repository(db_session, user=user, repo_full_name="acme/docs")
    assert result["status"] == "unchanged"
    assert result["files_indexed"] == 3


def test_github_sync_requires_connection(db_session):
    user = UserFactory()
    with pytest.raises(ValueError, match="not connected"):
        sync_repository(db_session, user=user, repo_full_name="acme/docs")


def test_github_decode_content():
    payload = {"encoding": "base64", "content": base64.b64encode(b"hello").decode()}
    assert _decode_content(payload) == "hello"
    assert _decode_content({"content": "plain"}) == "plain"


def test_redis_embedding_and_query_cache():
    cache_embedding("hello world", [0.1, 0.2])
    assert get_embedding_cache("hello world") == [0.1, 0.2]

    cache_query_result("graph_rag", "query-key", 1, {"nodes": []})
    assert get_query_cache("graph_rag", "query-key", 1) == {"nodes": []}


@patch("app.core.rbac.user_has_admin_access", return_value=True)
def test_github_connector_routes(_mock, auth_client, db_session):
    response = auth_client.get("/connectors/github/status", headers=auth_client.auth_headers)
    assert response.status_code == 200
    assert response.json()["connected"] is False

    with patch(
        "app.api.github_connector_routes.list_repositories",
        return_value=[{"full_name": "org/repo", "sync_status": "not_synced"}],
    ):
        response = auth_client.get("/connectors/github/repos", headers=auth_client.auth_headers)
    assert response.status_code == 200
    assert len(response.json()["repositories"]) == 1


@patch("app.core.admin_access.user_has_admin_access", return_value=True)
def test_analytics_cache_metrics_endpoint(_mock, auth_client):
    response = auth_client.get("/analytics/cache", headers=auth_client.auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "hits" in body
    assert "misses" in body


def test_workspace_connector_registry(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "secret")
    from app.core.app_settings import get_settings

    get_settings.cache_clear()
    connectors = list_connectors()
    github = get_connector("github")
    assert github is not None
    assert github["status"] == "configured"
    assert any(item["id"] == "github" for item in connectors)
    queued = sync_connector("github")
    assert queued["status"] == "queued"
    with pytest.raises(LookupError):
        sync_connector("unknown")
    assert get_connector("unknown") is None
    get_settings.cache_clear()
