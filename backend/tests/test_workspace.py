"""Tests for Phase D knowledge workspace features."""

from tests.factories import ChatSessionFactory


def test_folder_crud_and_session_organization(db_session, auth_client):
    from app.models.chat_session import ChatSession

    session = ChatSessionFactory(user=auth_client.auth_user)

    create = auth_client.post(
        "/folders",
        json={"name": "Work"},
        headers=auth_client.auth_headers,
    )
    assert create.status_code == 200
    folder_id = create.json()["id"]

    patch = auth_client.patch(
        f"/sessions/{session.id}/organization",
        json={"is_pinned": True, "folder_id": folder_id},
        headers=auth_client.auth_headers,
    )
    assert patch.status_code == 200
    body = patch.json()
    assert body["is_pinned"] is True
    assert body["folder_id"] == folder_id
    assert body["folder_name"] == "Work"

    listed = auth_client.get("/folders", headers=auth_client.auth_headers)
    assert listed.status_code == 200
    assert listed.json()[0]["session_count"] == 1

    db_session.refresh(session)
    assert session.is_pinned is True
    assert session.folder_id == folder_id

    deleted = auth_client.delete(f"/folders/{folder_id}", headers=auth_client.auth_headers)
    assert deleted.status_code == 200

    db_session.refresh(session)
    assert session.folder_id is None


def test_collection_update_delete_and_move_document(db_session, auth_client):
    from app.models.document import DocumentCollection, DocumentRecord

    user = auth_client.auth_user
    default = DocumentCollection(user_id=user.id, workspace_id="default", name="Default")
    custom = DocumentCollection(user_id=user.id, workspace_id="default", name="Research")
    db_session.add_all([default, custom])
    db_session.commit()

    document = DocumentRecord(
        user_id=user.id,
        workspace_id="default",
        collection_id=default.id,
        filename="notes.txt",
        storage_path="/tmp/notes.txt",
        file_size=32,
        chunks_created=1,
        indexing_stage="ready",
    )
    db_session.add(document)
    db_session.commit()

    renamed = auth_client.patch(
        f"/collections/{custom.id}",
        json={"name": "Reports"},
        headers=auth_client.auth_headers,
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Reports"

    moved = auth_client.patch(
        f"/documents/id/{document.id}/collection",
        json={"collection_id": custom.id},
        headers=auth_client.auth_headers,
    )
    assert moved.status_code == 200
    assert moved.json()["collection_id"] == custom.id

    deleted = auth_client.delete(f"/collections/{custom.id}", headers=auth_client.auth_headers)
    assert deleted.status_code == 200

    db_session.refresh(document)
    assert document.collection_id == default.id


def test_global_search_returns_messages_and_documents(db_session, auth_client):
    from app.models.document import DocumentCollection, DocumentRecord
    from app.models.message import Message

    user = auth_client.auth_user
    session = ChatSessionFactory(user=user, title="Billing Questions")
    collection = DocumentCollection(user_id=user.id, workspace_id="default", name="Default")
    db_session.add(collection)
    db_session.commit()

    db_session.add(
        Message(
            user_id=user.id,
            session_id=session.id,
            role="user",
            content="How do refunds work for annual plans?",
        )
    )
    db_session.add(
        DocumentRecord(
            user_id=user.id,
            workspace_id="default",
            collection_id=collection.id,
            filename="refund-policy.pdf",
            storage_path="/tmp/refund-policy.pdf",
            file_size=64,
            chunks_created=2,
            indexing_stage="ready",
        )
    )
    db_session.commit()

    response = auth_client.get("/search?q=refund", headers=auth_client.auth_headers)
    assert response.status_code == 200
    payload = response.json()
    types = {item["type"] for item in payload["results"]}
    assert "message" in types
    assert "document" in types
