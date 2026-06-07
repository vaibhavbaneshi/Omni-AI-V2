"""Document collection management helpers."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.document import DocumentCollection, DocumentRecord


def get_owned_collection(
    db: Session,
    *,
    user_id: int,
    collection_id: int,
) -> DocumentCollection | None:
    return (
        db.query(DocumentCollection)
        .filter(
            DocumentCollection.id == collection_id,
            DocumentCollection.user_id == user_id,
        )
        .first()
    )


def get_or_create_default_collection(
    db: Session,
    *,
    user_id: int,
    workspace_id: str = "default",
) -> DocumentCollection:
    collection = (
        db.query(DocumentCollection)
        .filter(
            DocumentCollection.user_id == user_id,
            DocumentCollection.workspace_id == workspace_id,
            DocumentCollection.name == "Default",
        )
        .first()
    )
    if collection:
        return collection

    collection = DocumentCollection(
        user_id=user_id,
        workspace_id=workspace_id,
        name="Default",
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection


def update_collection_name(
    db: Session,
    *,
    user_id: int,
    collection_id: int,
    name: str,
) -> DocumentCollection | None:
    collection = get_owned_collection(db, user_id=user_id, collection_id=collection_id)
    if not collection:
        return None

    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Collection name is required.")
    if collection.name == "Default" and cleaned != "Default":
        raise ValueError("The default collection cannot be renamed.")

    collection.name = cleaned
    db.commit()
    db.refresh(collection)
    return collection


def delete_collection(
    db: Session,
    *,
    user_id: int,
    collection_id: int,
) -> bool:
    collection = get_owned_collection(db, user_id=user_id, collection_id=collection_id)
    if not collection:
        return False
    if collection.name == "Default":
        raise ValueError("The default collection cannot be deleted.")

    default_collection = get_or_create_default_collection(
        db,
        user_id=user_id,
        workspace_id=collection.workspace_id,
    )

    (
        db.query(DocumentRecord)
        .filter(
            DocumentRecord.user_id == user_id,
            DocumentRecord.collection_id == collection.id,
        )
        .update({DocumentRecord.collection_id: default_collection.id}, synchronize_session=False)
    )

    db.delete(collection)
    db.commit()
    return True


def move_document_to_collection(
    db: Session,
    *,
    user_id: int,
    document_id: int,
    collection_id: int,
) -> DocumentRecord | None:
    document = (
        db.query(DocumentRecord)
        .filter(
            DocumentRecord.id == document_id,
            DocumentRecord.user_id == user_id,
        )
        .first()
    )
    if not document:
        return None

    collection = get_owned_collection(db, user_id=user_id, collection_id=collection_id)
    if not collection:
        raise ValueError("Collection not found.")

    document.collection_id = collection.id
    db.commit()
    db.refresh(document)
    return document


def collection_document_count(db: Session, *, collection_id: int) -> int:
    return (
        db.query(DocumentRecord)
        .filter(DocumentRecord.collection_id == collection_id)
        .count()
    )
