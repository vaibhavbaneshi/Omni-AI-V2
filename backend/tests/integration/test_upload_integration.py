"""Integration tests — document upload validation and ingestion."""

from io import BytesIO
import os
from unittest.mock import patch

from tests.factories import ChatSessionFactory


@patch("app.api.upload_routes.process_document", return_value=3)
def test_upload_txt_document(mock_process, auth_client, db_session):
    session = ChatSessionFactory(user=auth_client.auth_user, title="Upload Chat")

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
    assert not os.path.exists(mock_process.call_args.kwargs["file_path"])


@patch("app.api.upload_routes.process_document", return_value=4)
def test_upload_pdf_document(mock_process, auth_client, db_session):
    session = ChatSessionFactory(user=auth_client.auth_user, title="PDF Upload")

    response = auth_client.post(
        f"/upload?session_id={session.id}",
        headers=auth_client.auth_headers,
        files={"file": ("paper.pdf", BytesIO(b"%PDF-1.4\nbody"), "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["filename"] == "paper.pdf"
    assert response.json()["chunks_created"] == 4
    mock_process.assert_called_once()


@patch("app.api.upload_routes.process_document", return_value=5)
def test_upload_docx_document(mock_process, auth_client, db_session):
    session = ChatSessionFactory(user=auth_client.auth_user, title="DOCX Upload")

    response = auth_client.post(
        f"/upload?session_id={session.id}",
        headers=auth_client.auth_headers,
        files={
            "file": (
                "brief.docx",
                BytesIO(b"PK\x03\x04 fake office document"),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["filename"] == "brief.docx"
    assert response.json()["chunks_created"] == 5
    mock_process.assert_called_once()


def test_upload_rejects_unknown_extension(auth_client, db_session):
    session = ChatSessionFactory(user=auth_client.auth_user, title="Bad Upload")

    response = auth_client.post(
        f"/upload?session_id={session.id}",
        headers=auth_client.auth_headers,
        files={"file": ("image.png", BytesIO(b"PNG"), "image/png")},
    )
    assert response.status_code == 400


def test_upload_rejects_large_file(auth_client, db_session):
    session = ChatSessionFactory(user=auth_client.auth_user, title="Large Upload")
    large_body = b"x" * (15 * 1024 * 1024 + 1)

    response = auth_client.post(
        f"/upload?session_id={session.id}",
        headers=auth_client.auth_headers,
        files={"file": ("large.txt", BytesIO(large_body), "text/plain")},
    )

    assert response.status_code == 413


@patch("app.api.upload_routes.process_document", side_effect=RuntimeError("boom"))
def test_upload_processing_failure_returns_error(mock_process, auth_client, db_session):
    session = ChatSessionFactory(user=auth_client.auth_user, title="Failure Upload")

    response = auth_client.post(
        f"/upload?session_id={session.id}",
        headers=auth_client.auth_headers,
        files={"file": ("broken.txt", BytesIO(b"This will fail processing."), "text/plain")},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Document upload failed during processing. Check backend logs for details."
    )
    mock_process.assert_called_once()


def test_upload_requires_session_id(auth_client):
    response = auth_client.post(
        "/upload",
        headers=auth_client.auth_headers,
        files={"file": ("notes.txt", BytesIO(b"Hello."), "text/plain")},
    )
    assert response.status_code == 400
    assert "session_id" in response.json()["detail"].lower()


def test_list_documents_requires_session_scope(auth_client, db_session):
    response = auth_client.get("/documents", headers=auth_client.auth_headers)
    assert response.status_code == 200
    assert response.json()["documents"] == []


def test_list_documents_empty_for_session(auth_client, db_session):
    session = ChatSessionFactory(user=auth_client.auth_user, title="Empty Chat")
    response = auth_client.get(
        f"/documents?session_id={session.id}",
        headers=auth_client.auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["documents"] == []


@patch("app.api.upload_routes.process_document", return_value=2)
def test_delete_document_by_id(mock_process, auth_client, db_session):
    session = ChatSessionFactory(user=auth_client.auth_user, title="Delete Chat")

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


@patch("app.api.upload_routes.process_document", return_value=2)
def test_multiple_uploads(mock_process, auth_client, db_session):
    session = ChatSessionFactory(user=auth_client.auth_user, title="Many Uploads")

    for filename in ("one.txt", "two.txt"):
        response = auth_client.post(
            f"/upload?session_id={session.id}",
            headers=auth_client.auth_headers,
            files={"file": (filename, BytesIO(f"Content for {filename}".encode()), "text/plain")},
        )
        assert response.status_code == 200

    listed = auth_client.get(
        f"/documents?session_id={session.id}",
        headers=auth_client.auth_headers,
    )
    assert {item["filename"] for item in listed.json()["documents"]} == {"one.txt", "two.txt"}
    assert mock_process.call_count == 2
