"""User profile and workspace settings tables.

Revision ID: 20260525_0004
Revises: 20260525_0003
Create Date: 2026-05-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260525_0004"
down_revision: Union[str, None] = "20260525_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("first_name", sa.String(), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(), nullable=True))
    op.add_column("users", sa.Column("bio", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(), nullable=True))
    op.add_column("users", sa.Column("oauth_provider", sa.String(), nullable=True))
    op.add_column(
        "users",
        sa.Column("has_password", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column("users", sa.Column("password_changed_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("totp_secret", sa.String(), nullable=True))
    op.add_column(
        "users",
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column("users", sa.Column("created_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("updated_at", sa.DateTime(), nullable=True))

    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("default_model", sa.String(), nullable=False, server_default="auto"),
        sa.Column("response_style", sa.String(), nullable=False, server_default="balanced"),
        sa.Column("system_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("web_search_enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("code_execution_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("streaming_enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("theme", sa.String(), nullable=False, server_default="dark"),
        sa.Column("font_size", sa.String(), nullable=False, server_default="medium"),
        sa.Column("compact_mode", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("email_notifications", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("product_updates", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("usage_alerts", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_user_preferences_id", "user_preferences", ["id"])

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_jti", sa.String(), nullable=False, unique=True),
        sa.Column("device_label", sa.String(), nullable=False, server_default="Unknown device"),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("last_active_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_user_sessions_id", "user_sessions", ["id"])
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_session_jti", "user_sessions", ["session_jti"])

    op.create_table(
        "user_api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("key_prefix", sa.String(), nullable=False),
        sa.Column("key_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_user_api_keys_id", "user_api_keys", ["id"])

    op.create_table(
        "user_webhooks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("url", sa.String(), nullable=False, server_default=""),
        sa.Column("events", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_user_webhooks_id", "user_webhooks", ["id"])

    op.create_table(
        "billing_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("plan", sa.String(), nullable=False, server_default="free"),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("billing_cycle", sa.String(), nullable=False, server_default="monthly"),
        sa.Column("next_billing_date", sa.DateTime(), nullable=True),
        sa.Column("payment_method_brand", sa.String(), nullable=True),
        sa.Column("payment_method_last4", sa.String(), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_billing_subscriptions_id", "billing_subscriptions", ["id"])

    op.create_table(
        "billing_invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="paid"),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("invoice_date", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_billing_invoices_id", "billing_invoices", ["id"])
    op.create_index("ix_billing_invoices_user_id", "billing_invoices", ["user_id"])


def downgrade() -> None:
    op.drop_table("billing_invoices")
    op.drop_table("billing_subscriptions")
    op.drop_table("user_webhooks")
    op.drop_table("user_api_keys")
    op.drop_table("user_sessions")
    op.drop_table("user_preferences")
    for column in (
        "updated_at",
        "created_at",
        "totp_enabled",
        "totp_secret",
        "password_changed_at",
        "has_password",
        "oauth_provider",
        "avatar_url",
        "bio",
        "last_name",
        "first_name",
    ):
        op.drop_column("users", column)
