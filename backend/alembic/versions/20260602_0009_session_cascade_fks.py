"""Cascade chat session deletes to child rows (messages, documents, summaries)."""

from typing import Sequence, Union

from alembic import op

revision: str = "20260602_0009"
down_revision: Union[str, None] = "20260601_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _replace_fk(
    *,
    table: str,
    constraint: str,
    referent: str,
    local_cols: list[str],
    remote_cols: list[str],
    ondelete: str,
) -> None:
    op.drop_constraint(constraint, table, type_="foreignkey")
    op.create_foreign_key(
        constraint,
        table,
        referent,
        local_cols,
        remote_cols,
        ondelete=ondelete,
    )


def upgrade() -> None:
    _replace_fk(
        table="messages",
        constraint="messages_session_id_fkey",
        referent="chat_sessions",
        local_cols=["session_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )
    _replace_fk(
        table="conversation_summaries",
        constraint="conversation_summaries_session_id_fkey",
        referent="chat_sessions",
        local_cols=["session_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )
    _replace_fk(
        table="documents",
        constraint="fk_documents_session_id",
        referent="chat_sessions",
        local_cols=["session_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )
    _replace_fk(
        table="model_usage",
        constraint="model_usage_session_id_fkey",
        referent="chat_sessions",
        local_cols=["session_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )
    _replace_fk(
        table="token_usage",
        constraint="token_usage_session_id_fkey",
        referent="chat_sessions",
        local_cols=["session_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    _replace_fk(
        table="messages",
        constraint="messages_session_id_fkey",
        referent="chat_sessions",
        local_cols=["session_id"],
        remote_cols=["id"],
        ondelete="NO ACTION",
    )
    _replace_fk(
        table="conversation_summaries",
        constraint="conversation_summaries_session_id_fkey",
        referent="chat_sessions",
        local_cols=["session_id"],
        remote_cols=["id"],
        ondelete="NO ACTION",
    )
    _replace_fk(
        table="documents",
        constraint="fk_documents_session_id",
        referent="chat_sessions",
        local_cols=["session_id"],
        remote_cols=["id"],
        ondelete="NO ACTION",
    )
    _replace_fk(
        table="model_usage",
        constraint="model_usage_session_id_fkey",
        referent="chat_sessions",
        local_cols=["session_id"],
        remote_cols=["id"],
        ondelete="NO ACTION",
    )
    _replace_fk(
        table="token_usage",
        constraint="token_usage_session_id_fkey",
        referent="chat_sessions",
        local_cols=["session_id"],
        remote_cols=["id"],
        ondelete="NO ACTION",
    )
