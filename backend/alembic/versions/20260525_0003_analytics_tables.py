"""Analytics tables for API, model, and token usage.

Revision ID: 20260525_0003
Revises: 20260525_0002
Create Date: 2026-05-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260525_0003"
down_revision: Union[str, None] = "20260525_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_api_usage_id", "api_usage", ["id"])
    op.create_index("ix_api_usage_user_id", "api_usage", ["user_id"])
    op.create_index("ix_api_usage_path", "api_usage", ["path"])
    op.create_index("ix_api_usage_trace_id", "api_usage", ["trace_id"])
    op.create_index("ix_api_usage_created_at", "api_usage", ["created_at"])

    op.create_table(
        "model_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("chat_sessions.id"), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("endpoint", sa.String(length=128), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_model_usage_id", "model_usage", ["id"])
    op.create_index("ix_model_usage_user_id", "model_usage", ["user_id"])
    op.create_index("ix_model_usage_session_id", "model_usage", ["session_id"])
    op.create_index("ix_model_usage_created_at", "model_usage", ["created_at"])

    op.create_table(
        "token_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("chat_sessions.id"), nullable=True),
        sa.Column("model_usage_id", sa.Integer(), sa.ForeignKey("model_usage.id"), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("prompt_chars", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_chars", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_token_usage_id", "token_usage", ["id"])
    op.create_index("ix_token_usage_user_id", "token_usage", ["user_id"])
    op.create_index("ix_token_usage_session_id", "token_usage", ["session_id"])
    op.create_index("ix_token_usage_model_usage_id", "token_usage", ["model_usage_id"])
    op.create_index("ix_token_usage_created_at", "token_usage", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_token_usage_created_at", table_name="token_usage")
    op.drop_index("ix_token_usage_model_usage_id", table_name="token_usage")
    op.drop_index("ix_token_usage_session_id", table_name="token_usage")
    op.drop_index("ix_token_usage_user_id", table_name="token_usage")
    op.drop_index("ix_token_usage_id", table_name="token_usage")
    op.drop_table("token_usage")

    op.drop_index("ix_model_usage_created_at", table_name="model_usage")
    op.drop_index("ix_model_usage_session_id", table_name="model_usage")
    op.drop_index("ix_model_usage_user_id", table_name="model_usage")
    op.drop_index("ix_model_usage_id", table_name="model_usage")
    op.drop_table("model_usage")

    op.drop_index("ix_api_usage_created_at", table_name="api_usage")
    op.drop_index("ix_api_usage_trace_id", table_name="api_usage")
    op.drop_index("ix_api_usage_path", table_name="api_usage")
    op.drop_index("ix_api_usage_user_id", table_name="api_usage")
    op.drop_index("ix_api_usage_id", table_name="api_usage")
    op.drop_table("api_usage")
