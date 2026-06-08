"""Additional coverage for services with gaps after Phase L."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.collection_service import (
    delete_collection,
    get_or_create_default_collection,
    get_owned_collection,
    update_collection_name,
)
from app.services.redis_cache_service import get_cached, set_cached
from app.services.title_service import generate_chat_title, optimistic_chat_title
from app.services.upload_security_service import (
    UploadSecurityError,
    check_zip_bomb,
    scan_with_clamav,
)
from tests.factories import ChatSessionFactory, UserFactory


def test_collection_service_crud(db_session):
    user = UserFactory()
    other = UserFactory()
    default = get_or_create_default_collection(db_session, user_id=user.id)
    assert default.name == "Default"
    assert get_owned_collection(db_session, user_id=other.id, collection_id=default.id) is None

    with pytest.raises(ValueError, match="cannot be renamed"):
        update_collection_name(
            db_session,
            user_id=user.id,
            collection_id=default.id,
            name="Renamed",
        )

    with pytest.raises(ValueError, match="cannot be deleted"):
        delete_collection(db_session, user_id=user.id, collection_id=default.id)


@patch("app.services.redis_cache_service._redis_client", return_value=None)
def test_redis_cache_memory_fallback(_mock_client):
    set_cached("test", "key", value={"ok": True})
    assert get_cached("test", "key") == {"ok": True}


def test_check_zip_bomb_rejects_too_many_entries(tmp_path):
    archive_path = tmp_path / "many.zip"
    with patch("app.services.upload_security_service.MAX_ZIP_ENTRIES", 1):
        with __import__("zipfile").ZipFile(archive_path, "w") as archive:
            archive.writestr("a.txt", "1")
            archive.writestr("b.txt", "2")
        with pytest.raises(UploadSecurityError, match="too many entries"):
            check_zip_bomb(str(archive_path))


def test_scan_with_clamav_missing_binary_when_required(monkeypatch, tmp_path):
    sample = tmp_path / "file.txt"
    sample.write_text("data")
    monkeypatch.setenv("CLAMAV_ENABLED", "true")
    monkeypatch.setenv("CLAMAV_REQUIRED", "true")
    from app.core.app_settings import get_settings

    get_settings.cache_clear()
    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(UploadSecurityError, match="required"):
            scan_with_clamav(str(sample))
    get_settings.cache_clear()


@patch("app.services.title_service.invoke_generate")
def test_generate_chat_title_fallback(mock_invoke):
    mock_invoke.return_value = "  Quarterly Planning  "
    title = generate_chat_title("Summarize our Q3 roadmap and blockers")
    assert title == "Quarterly Planning"


@patch("app.services.title_service.invoke_generate", side_effect=RuntimeError("llm down"))
def test_generate_chat_title_uses_query_prefix_on_failure(_mock_invoke):
    title = generate_chat_title("Explain vector database sharding strategies in detail")
    assert title == optimistic_chat_title("Explain vector database sharding strategies in detail")
