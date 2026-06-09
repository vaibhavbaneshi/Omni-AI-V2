"""GitHub connector — OAuth, repo listing, sync, indexing."""

from __future__ import annotations

import io
import logging
import os
import tarfile
import tempfile
from datetime import datetime
from typing import Any
from urllib.parse import quote, urlencode

import httpx
from sqlalchemy.orm import Session
from app.core.app_settings import get_settings
from app.core.oauth_config import get_oauth_settings
from app.models.document import DocumentCollection, DocumentRecord
from app.models.github_connector import GitHubConnection, GitHubRepositorySync
from app.models.user import User
from app.services.oauth_service import decode_oauth_state, encode_oauth_state, exchange_github_code
from app.services.security_audit_service import audit_log

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
GITHUB_OAUTH_SCOPES = "read:user user:email repo"
INDEXABLE_EXTENSIONS = {
    ".md",
    ".markdown",
    ".txt",
    ".rst",
    ".py",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".vue",
    ".java",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".sql",
    ".sh",
    ".bash",
    ".xml",
    ".csv",
    ".ini",
    ".cfg",
    ".conf",
    ".env",
    ".dockerfile",
}
SKIP_PATH_SEGMENTS = {
    "node_modules",
    ".git",
    "dist",
    "build",
    ".next",
    "coverage",
    "vendor",
    "__pycache__",
    ".venv",
    "venv",
    "target",
    "bin",
    "obj",
    ".idea",
    ".vscode",
    ".cache",
    "chroma_db",
    ".turbo",
    ".pnpm-store",
}
MAX_INDEXABLE_FILE_BYTES = 512_000
MAX_FILES_PER_SYNC = 500
SKIP_FILENAMES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "cargo.lock",
    ".coverage",
}


def github_oauth_redirect_uri() -> str:
    settings = get_oauth_settings()
    return f"{settings['api_public_url']}/auth/github/callback"


def get_connection(db: Session, *, user_id: int) -> GitHubConnection | None:
    return db.query(GitHubConnection).filter(GitHubConnection.user_id == user_id).first()


def save_connection(
    db: Session,
    *,
    user_id: int,
    github_user_id: str,
    github_login: str,
    access_token: str,
    scopes: str | None = None,
) -> GitHubConnection:
    record = get_connection(db, user_id=user_id)
    if record is None:
        record = GitHubConnection(
            user_id=user_id,
            github_user_id=github_user_id,
            github_login=github_login,
            access_token=access_token,
            scopes=scopes,
        )
        db.add(record)
    else:
        record.github_user_id = github_user_id
        record.github_login = github_login
        record.access_token = access_token
        record.scopes = scopes
    db.commit()
    db.refresh(record)
    return record


def build_connector_authorize_url(*, user_id: int, next_path: str = "/chat") -> str:
    settings = get_oauth_settings()
    state = encode_oauth_state("github_connector", next_path, user_id=user_id)
    params = urlencode(
        {
            "client_id": settings["github_client_id"],
            "redirect_uri": github_oauth_redirect_uri(),
            "scope": GITHUB_OAUTH_SCOPES,
            "state": state,
        }
    )
    return f"https://github.com/login/oauth/authorize?{params}"


def link_github_account_from_login(
    db: Session,
    *,
    user_id: int,
    access_token: str,
    profile: dict[str, str],
) -> GitHubConnection:
    return save_connection(
        db,
        user_id=user_id,
        github_user_id=profile["github_user_id"],
        github_login=profile["github_login"],
        access_token=access_token,
        scopes=GITHUB_OAUTH_SCOPES,
    )


def connect_github_account_from_token(
    db: Session,
    *,
    user: User,
    access_token: str,
) -> GitHubConnection:
    profile = _github_get(access_token, "/user")
    return save_connection(
        db,
        user_id=user.id,
        github_user_id=str(profile["id"]),
        github_login=profile["login"],
        access_token=access_token,
        scopes=GITHUB_OAUTH_SCOPES,
    )


def handle_connector_callback(
    db: Session,
    *,
    user: User,
    code: str,
    state: str,
) -> GitHubConnection:
    decode_oauth_state(state)
    settings = get_oauth_settings()
    access_token = exchange_github_code(
        client_id=settings["github_client_id"],
        client_secret=settings["github_client_secret"],
        code=code,
        redirect_uri=github_oauth_redirect_uri(),
    )
    return connect_github_account_from_token(db, user=user, access_token=access_token)


def list_repositories(db: Session, *, user_id: int) -> list[dict[str, Any]]:
    connection = get_connection(db, user_id=user_id)
    if not connection:
        return []
    repos = _github_get(connection.access_token, "/user/repos", params={"per_page": 100, "sort": "updated"})
    syncs = {
        row.repo_full_name: row
        for row in db.query(GitHubRepositorySync).filter(GitHubRepositorySync.user_id == user_id).all()
    }
    return [
        {
            "full_name": repo["full_name"],
            "private": repo.get("private", False),
            "default_branch": repo.get("default_branch", "main"),
            "description": repo.get("description"),
            "sync_status": syncs.get(repo["full_name"]).sync_status if repo["full_name"] in syncs else "not_synced",
            "sync_error": (
                (syncs[repo["full_name"]].sync_metadata or {}).get("error")
                if repo["full_name"] in syncs and syncs[repo["full_name"]].sync_metadata
                else None
            ),
            "files_indexed": (
                syncs[repo["full_name"]].files_indexed if repo["full_name"] in syncs else 0
            ),
            "candidates_seen": (
                (syncs[repo["full_name"]].sync_metadata or {}).get("candidates_seen")
                if repo["full_name"] in syncs and syncs[repo["full_name"]].sync_metadata
                else None
            ),
            "last_sync_at": (
                syncs[repo["full_name"]].last_sync_at.isoformat()
                if repo["full_name"] in syncs and syncs[repo["full_name"]].last_sync_at
                else None
            ),
        }
        for repo in repos
    ]


def sync_repository(
    db: Session,
    *,
    user: User,
    repo_full_name: str,
    workspace_id: str = "default",
    session_id: int | None = None,
) -> dict[str, Any]:
    connection = get_connection(db, user_id=user.id)
    if not connection:
        raise ValueError("GitHub is not connected. Authorize the connector first.")

    sync = (
        db.query(GitHubRepositorySync)
        .filter(
            GitHubRepositorySync.user_id == user.id,
            GitHubRepositorySync.repo_full_name == repo_full_name,
        )
        .first()
    )

    try:
        repo = _github_get(connection.access_token, f"/repos/{repo_full_name}")
        branch = repo.get("default_branch", "main")
        commit = _github_get(connection.access_token, f"/repos/{repo_full_name}/commits/{branch}")
        commit_sha = commit["sha"]

        if (
            sync
            and sync.last_commit_sha == commit_sha
            and sync.sync_status == "complete"
            and sync.files_indexed > 0
        ):
            return {"status": "unchanged", "files_indexed": sync.files_indexed, "commit_sha": commit_sha}

        collection = _ensure_collection(db, user=user, workspace_id=workspace_id)
        if sync is None:
            sync = GitHubRepositorySync(
                user_id=user.id,
                connection_id=connection.id,
                repo_full_name=repo_full_name,
                default_branch=branch,
                workspace_id=workspace_id,
                collection_id=collection.id,
            )
            db.add(sync)
        sync.sync_status = "running"
        sync.collection_id = collection.id
        sync.sync_metadata = None
        db.commit()

        index_stats = _index_repo_from_tarball(
            db,
            connection=connection,
            user=user,
            repo_full_name=repo_full_name,
            branch=branch,
            collection_id=collection.id,
            workspace_id=workspace_id,
            session_id=session_id,
        )

        sync.last_sync_at = datetime.utcnow()
        sync.last_commit_sha = commit_sha
        sync.sync_status = "complete"
        sync.files_indexed = index_stats["files_indexed"]
        sync.sync_metadata = {
            "branch": branch,
            "commit_sha": commit_sha,
            "method": "tarball",
            **index_stats,
        }
        db.commit()

        audit_log(
            db,
            action="connector.github.sync",
            user_id=user.id,
            detail={
                "repo": repo_full_name,
                "files_indexed": index_stats["files_indexed"],
                "commit_sha": commit_sha,
                "method": "tarball",
            },
        )
        return {
            "status": "complete",
            "files_indexed": index_stats["files_indexed"],
            "commit_sha": commit_sha,
            **index_stats,
        }
    except httpx.HTTPStatusError as exc:
        message = _github_http_error_message(exc, repo_full_name=repo_full_name)
        _mark_sync_failed(db, sync=sync, error=message)
        raise ValueError(message) from exc
    except Exception as exc:
        message = str(exc).strip() or "GitHub sync failed."
        _mark_sync_failed(db, sync=sync, error=message)
        raise ValueError(message) from exc


def _mark_sync_failed(db: Session, *, sync: GitHubRepositorySync | None, error: str) -> None:
    if sync is None:
        return
    sync.sync_status = "failed"
    sync.sync_metadata = {"error": error[:500]}
    db.commit()


def _github_http_error_message(exc: httpx.HTTPStatusError, *, repo_full_name: str) -> str:
    if exc.response.status_code == 401:
        return "GitHub authorization expired. Sign in with GitHub again or reconnect the connector."
    if exc.response.status_code == 403:
        return (
            f"GitHub denied access to {repo_full_name}. "
            "Reconnect the connector and grant repository access."
        )
    if exc.response.status_code == 404:
        return f"Repository {repo_full_name} was not found or you do not have access."
    if exc.response.status_code == 409:
        return f"Repository {repo_full_name} is empty or has no commits on the default branch."
    return f"GitHub sync failed ({exc.response.status_code}). Please try again."


def run_github_sync_job(*, user_id: int, repo_full_name: str, workspace_id: str = "default") -> None:
    """Background worker entrypoint — uses its own DB session."""
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error("GitHub sync aborted: user %s not found", user_id)
            return
        sync_repository(
            db,
            user=user,
            repo_full_name=repo_full_name,
            workspace_id=workspace_id,
            session_id=None,
        )
    except Exception as exc:
        logger.exception("Background GitHub sync failed for %s (user=%s)", repo_full_name, user_id)
        sync = (
            db.query(GitHubRepositorySync)
            .filter(
                GitHubRepositorySync.user_id == user_id,
                GitHubRepositorySync.repo_full_name == repo_full_name,
            )
            .first()
        )
        if sync and sync.sync_status == "running":
            _mark_sync_failed(db, sync=sync, error=str(exc)[:500] or "GitHub sync failed.")
    finally:
        db.close()


def _index_repo_from_tarball(
    db: Session,
    *,
    connection: GitHubConnection,
    user: User,
    repo_full_name: str,
    branch: str,
    collection_id: int,
    workspace_id: str,
    session_id: int | None,
) -> dict[str, int]:
    archive_bytes = _download_repo_tarball(connection.access_token, repo_full_name, branch)
    stats = {
        "files_indexed": 0,
        "skipped_files": 0,
        "skipped_ignored_path": 0,
        "skipped_extension": 0,
        "skipped_too_large": 0,
        "candidates_seen": 0,
        "truncated": 0,
    }

    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:*") as archive:
        root_prefix = _tarball_root_prefix(archive.getmembers())
        for member in archive.getmembers():
            if not member.isfile():
                continue
            relative_path = _tarball_relative_path(member.name, root_prefix)
            if not relative_path:
                continue
            stats["candidates_seen"] += 1
            if _should_skip_repo_path(relative_path):
                stats["skipped_ignored_path"] += 1
                continue
            basename = os.path.basename(relative_path)
            if basename.lower() in SKIP_FILENAMES:
                stats["skipped_files"] += 1
                continue
            ext = os.path.splitext(relative_path)[1].lower()
            if ext == "" and basename.lower() == "dockerfile":
                ext = ".dockerfile"
            if ext not in INDEXABLE_EXTENSIONS:
                stats["skipped_extension"] += 1
                continue
            if member.size and member.size > MAX_INDEXABLE_FILE_BYTES:
                stats["skipped_too_large"] += 1
                continue
            if stats["files_indexed"] >= MAX_FILES_PER_SYNC:
                stats["truncated"] = 1
                break
            try:
                extracted = archive.extractfile(member)
                if extracted is None:
                    stats["skipped_files"] += 1
                    continue
                text = extracted.read().decode("utf-8", errors="replace")
                if not text.strip():
                    continue
                _index_github_file(
                    db,
                    user=user,
                    collection_id=collection_id,
                    workspace_id=workspace_id,
                    session_id=session_id,
                    repo_full_name=repo_full_name,
                    path=relative_path,
                    text=text,
                )
                stats["files_indexed"] += 1
            except Exception as exc:
                stats["skipped_files"] += 1
                logger.warning(
                    "Skipped GitHub file %s/%s: %s",
                    repo_full_name,
                    relative_path,
                    exc,
                )

    return stats


def _download_repo_tarball(token: str, repo_full_name: str, branch: str) -> bytes:
    owner, repo = repo_full_name.split("/", 1)
    url = f"{GITHUB_API}/repos/{owner}/{repo}/tarball/{quote(branch, safe='')}"
    last_response: httpx.Response | None = None
    for auth_scheme in (f"Bearer {token}", f"token {token}"):
        headers = {
            "Authorization": auth_scheme,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        last_response = httpx.get(url, headers=headers, follow_redirects=True, timeout=180)
        if last_response.status_code != 401:
            break
    assert last_response is not None
    last_response.raise_for_status()
    return last_response.content


def _tarball_root_prefix(members: list[tarfile.TarInfo]) -> str:
    for member in members:
        if member.isfile() and "/" in member.name:
            return member.name.split("/", 1)[0] + "/"
    return ""


def _tarball_relative_path(member_name: str, root_prefix: str) -> str:
    if root_prefix and member_name.startswith(root_prefix):
        return member_name[len(root_prefix) :]
    if "/" in member_name:
        return member_name.split("/", 1)[1]
    return member_name


def _ensure_collection(db: Session, *, user: User, workspace_id: str) -> DocumentCollection:
    collection = (
        db.query(DocumentCollection)
        .filter(
            DocumentCollection.user_id == user.id,
            DocumentCollection.workspace_id == workspace_id,
            DocumentCollection.name == "GitHub",
        )
        .first()
    )
    if collection:
        return collection
    collection = DocumentCollection(user_id=user.id, workspace_id=workspace_id, name="GitHub")
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection


def _index_github_file(
    db: Session,
    *,
    user: User,
    collection_id: int,
    workspace_id: str,
    session_id: int | None,
    repo_full_name: str,
    path: str,
    text: str,
) -> None:
    filename = f"{repo_full_name}/{path}".replace("/", "__")
    with tempfile.NamedTemporaryFile(mode="w", suffix=os.path.splitext(path)[1] or ".txt", delete=False) as tmp:
        tmp.write(text)
        storage_path = tmp.name

    document = DocumentRecord(
        user_id=user.id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        session_id=session_id,
        filename=filename,
        storage_path=storage_path,
        file_size=len(text.encode("utf-8")),
        chunks_created=0,
        indexing_stage="queued",
        security_status="approved",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    from app.services.ingestion_queue import dispatch_document_ingestion, ingest_queue_enabled
    from app.core.app_settings import get_settings

    settings = get_settings()
    if settings.INGEST_IN_BACKGROUND and ingest_queue_enabled():
        dispatch_document_ingestion(db, document.id)
    else:
        from app.services.ingestion_service import run_ingest_document_record

        run_ingest_document_record(db, document.id)


def _should_skip_repo_path(path: str) -> bool:
    parts = path.replace("\\", "/").split("/")
    return any(part in SKIP_PATH_SEGMENTS for part in parts)


def _fetch_blob_text(token: str, repo_full_name: str, blob_sha: str) -> str:
    import base64

    payload = _github_get(token, f"/repos/{repo_full_name}/git/blobs/{blob_sha}")
    content = payload.get("content")
    if not content:
        return ""
    if payload.get("encoding") == "base64":
        cleaned = content.replace("\n", "").replace("\r", "")
        return base64.b64decode(cleaned).decode("utf-8", errors="replace")
    return str(content)


def _github_get(token: str, path: str, params: dict | None = None) -> Any:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    response = httpx.get(f"{GITHUB_API}{path}", headers=headers, params=params, timeout=60)
    response.raise_for_status()
    return response.json()


def _github_get_raw(token: str, path: str, params: dict | None = None) -> dict:
    return _github_get(token, path, params=params)


def _decode_content(payload: dict) -> str:
    import base64

    encoding = payload.get("encoding")
    if encoding == "base64":
        return base64.b64decode(payload.get("content", "")).decode("utf-8", errors="replace")
    return payload.get("content") or ""
