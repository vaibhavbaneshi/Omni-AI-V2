"""Phases M-P: autonomous agents, connectors hub, marketplace, notifications.

Revision ID: 20260608_0016
Revises: 20260607_0015
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260608_0016"
down_revision = "20260607_0015"
branch_labels = None
depends_on = None

JSON = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    op.create_table(
        "autonomous_agents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("workspace_id", sa.String(64), nullable=False, server_default="default"),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("agent_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("config", JSON, nullable=True),
        sa.Column("schedule_kind", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("schedule_config", JSON, nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("template_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_autonomous_agents_status", "autonomous_agents", ["status"])

    op.create_table(
        "agent_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("autonomous_agents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="running"),
        sa.Column("trigger", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("output", JSON, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "agent_memory_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("autonomous_agents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("execution_id", sa.Integer(), sa.ForeignKey("agent_executions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("memory_type", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("category", sa.String(64), nullable=False, server_default="system"),
        sa.Column("link", sa.String(512), nullable=True),
        sa.Column("read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "connector_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("connector_type", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(256), nullable=True),
        sa.Column("credentials_encrypted", sa.Text(), nullable=False),
        sa.Column("metadata", JSON, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="connected"),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("document_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "connector_type", name="uq_connector_connections_user_type"),
    )

    op.create_table(
        "connector_sync_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("connection_id", sa.Integer(), sa.ForeignKey("connector_connections.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="running"),
        sa.Column("files_synced", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sync_metadata", JSON, nullable=True),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "marketplace_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(128), nullable=False, unique=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("config", JSON, nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("author_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("current_version", sa.String(32), nullable=False, server_default="1.0.0"),
        sa.Column("install_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "marketplace_template_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("marketplace_templates.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("config", JSON, nullable=False),
        sa.Column("changelog", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("template_id", "version", name="uq_marketplace_template_version"),
    )

    op.create_table(
        "marketplace_installs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("marketplace_templates.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("autonomous_agents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("installed_version", sa.String(32), nullable=False),
        sa.Column("favorited", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("installed_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "template_id", name="uq_marketplace_install_user_template"),
    )

    op.create_foreign_key(
        "fk_autonomous_agents_template_id",
        "autonomous_agents",
        "marketplace_templates",
        ["template_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_autonomous_agents_template_id", "autonomous_agents", type_="foreignkey")
    op.drop_table("marketplace_installs")
    op.drop_table("marketplace_template_versions")
    op.drop_table("marketplace_templates")
    op.drop_table("connector_sync_runs")
    op.drop_table("connector_connections")
    op.drop_table("notifications")
    op.drop_table("agent_memory_entries")
    op.drop_table("agent_executions")
    op.drop_index("ix_autonomous_agents_status", "autonomous_agents")
    op.drop_table("autonomous_agents")
