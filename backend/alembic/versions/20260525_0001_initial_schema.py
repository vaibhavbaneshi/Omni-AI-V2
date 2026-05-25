"""Initial Omni-AI schema.

Revision ID: 20260525_0001
Revises:
Create Date: 2026-05-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260525_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(), nullable=False, unique=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("password", sa.String(), nullable=False),
    )
    op.create_index("ix_users_id", "users", ["id"])

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False, server_default="default"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_chat_sessions_id", "chat_sessions", ["id"])
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])
    op.create_index("ix_chat_sessions_workspace_id", "chat_sessions", ["workspace_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("chat_sessions.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_messages_id", "messages", ["id"])
    op.create_index("ix_messages_user_id", "messages", ["user_id"])

    op.create_table(
        "conversation_summaries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("chat_sessions.id"), unique=True),
        sa.Column("summary", sa.Text(), nullable=True),
    )

    op.create_table(
        "document_collections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False, server_default="default"),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_document_collections_id", "document_collections", ["id"])
    op.create_index("ix_document_collections_user_id", "document_collections", ["user_id"])
    op.create_index("ix_document_collections_workspace_id", "document_collections", ["workspace_id"])

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("collection_id", sa.Integer(), sa.ForeignKey("document_collections.id"), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False, server_default="default"),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("storage_path", sa.String(), nullable=False),
        sa.Column("chunks_created", sa.Integer(), server_default="0"),
        sa.Column("embedding_version", sa.String(), nullable=False, server_default="bge-small-en-v1.5"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_documents_id", "documents", ["id"])
    op.create_index("ix_documents_user_id", "documents", ["user_id"])
    op.create_index("ix_documents_collection_id", "documents", ["collection_id"])
    op.create_index("ix_documents_workspace_id", "documents", ["workspace_id"])

    op.create_table(
        "user_memories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False, server_default="default"),
        sa.Column("category", sa.String(), nullable=False, server_default="preference"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("importance", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_user_memories_id", "user_memories", ["id"])
    op.create_index("ix_user_memories_user_id", "user_memories", ["user_id"])
    op.create_index("ix_user_memories_workspace_id", "user_memories", ["workspace_id"])


def downgrade() -> None:
    op.drop_table("user_memories")
    op.drop_table("documents")
    op.drop_table("document_collections")
    op.drop_table("conversation_summaries")
    op.drop_table("messages")
    op.drop_table("chat_sessions")
    op.drop_table("users")
