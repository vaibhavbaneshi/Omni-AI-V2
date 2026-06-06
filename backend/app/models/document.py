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

    session_id = Column(
        Integer,
        ForeignKey("chat_sessions.id"),
        nullable=True,
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

    file_size = Column(
        Integer,
        nullable=False,
        default=0
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

    indexing_stage = Column(
        String,
        nullable=False,
        default="queued",
    )

    indexing_error = Column(
        String,
        nullable=True,
    )

    indexing_started_at = Column(
        DateTime,
        nullable=True,
    )

    indexing_updated_at = Column(
        DateTime,
        nullable=True,
    )

    embeddings_completed = Column(
        Integer,
        default=0,
    )

    indexing_job_id = Column(
        String,
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
