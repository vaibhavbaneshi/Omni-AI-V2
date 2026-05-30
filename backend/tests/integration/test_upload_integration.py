"""Integration tests — document upload validation and ingestion."""

from io import BytesIO
from unittest.mock import patch

from tests.factories import ChatSessionFactory


@patch("app.api.upload_routes.process_document", return_value=3)
def test_upload_txt_document(mock_process, auth_client, db_session, tmp_path):
    session = ChatSessionFactory(user=auth_client.auth_user, title="Upload Chat")

    with patch("app.api.upload_routes.UPLOAD_DIR", str(tmp_path / "uploads")):
        response = auth_client.post(
            f"/upload?session_id={session.id}",
            headers=auth_client.auth_headers,
            files={"file": ("notes.txt", BytesIO(b"Hello from integration test."), "text/plain")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "notes.txt"
    assert payload["chunks_created"] == 3
    mock_process.assert_called_once()


def test_upload_rejects_unknown_extension(auth_client, db_session):
    session = ChatSessionFactory(user=auth_client.auth_user, title="Bad Upload")

    response = auth_client.post(
        f"/upload?session_id={session.id}",
        headers=auth_client.auth_headers,
        files={"file": ("image.png", BytesIO(b"PNG"), "image/png")},
    )
    assert response.status_code == 400


def test_list_documents_empty(auth_client):
    response = auth_client.get("/documents", headers=auth_client.auth_headers)
    assert response.status_code == 200
    assert response.json()["documents"] == []


@patch("app.api.upload_routes.process_document", return_value=2)
def test_delete_document_by_id(mock_process, auth_client, db_session, tmp_path):
    session = ChatSessionFactory(user=auth_client.auth_user, title="Delete Chat")

    with patch("app.api.upload_routes.UPLOAD_DIR", str(tmp_path / "uploads")):
        upload = auth_client.post(
            f"/upload?session_id={session.id}",
            headers=auth_client.auth_headers,
            files={"file": ("delete-me.txt", BytesIO(b"Delete this file."), "text/plain")},
        )

    document_id = upload.json()["document_id"]

    with patch("app.api.upload_routes.get_document_collection") as mock_collection:
        mock_collection.return_value.get.return_value = {"ids": ["chunk-1"]}
        response = auth_client.delete(
            f"/documents/id/{document_id}",
            headers=auth_client.auth_headers,
        )

    assert response.status_code == 200
    assert response.json()["document_id"] == document_id

    listed = auth_client.get(
        f"/documents?session_id={session.id}",
        headers=auth_client.auth_headers,
    )
    assert listed.json()["documents"] == []
