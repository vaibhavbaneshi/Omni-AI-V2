from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String
)

from app.db.database import Base


class DocumentCollection(Base):

    __tablename__ = "document_collections"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    workspace_id = Column(
        String,
        nullable=False,
        default="default",
        index=True
    )

    name = Column(
        String,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class DocumentRecord(Base):

    __tablename__ = "documents"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    collection_id = Column(
        Integer,
        ForeignKey("document_collections.id"),
        nullable=False,
        index=True
    )

    workspace_id = Column(
        String,
        nullable=False,
        default="default",
        index=True
    )

    filename = Column(
        String,
        nullable=False
    )

    storage_path = Column(
        String,
        nullable=False
    )

    chunks_created = Column(
        Integer,
        default=0
    )

    embedding_version = Column(
        String,
        nullable=False,
        default="bge-small-en-v1.5"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
