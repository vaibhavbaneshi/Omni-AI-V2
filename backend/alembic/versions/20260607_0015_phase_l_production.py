"""Phase L — GitHub connector, upload security status."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260607_0015"
down_revision: Union[str, None] = "20260606_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("security_status", sa.String(length=32), nullable=False, server_default="approved"),
    )

    op.create_table(
        "github_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("github_user_id", sa.String(length=64), nullable=False),
        sa.Column("github_login", sa.String(length=128), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("scopes", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", name="uq_github_connections_user_id"),
    )
    op.create_index("ix_github_connections_user_id", "github_connections", ["user_id"])

    op.create_table(
        "github_repository_syncs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connection_id", sa.Integer(), sa.ForeignKey("github_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("repo_full_name", sa.String(length=256), nullable=False),
        sa.Column("default_branch", sa.String(length=128), nullable=False, server_default="main"),
        sa.Column("workspace_id", sa.String(length=64), nullable=False, server_default="default"),
        sa.Column("collection_id", sa.Integer(), sa.ForeignKey("document_collections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("last_commit_sha", sa.String(length=64), nullable=True),
        sa.Column("sync_status", sa.String(length=32), nullable=False, server_default="idle"),
        sa.Column("files_indexed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "repo_full_name", name="uq_github_repo_sync"),
    )
    op.create_index("ix_github_repository_syncs_user_id", "github_repository_syncs", ["user_id"])
    op.create_index("ix_github_repository_syncs_repo_full_name", "github_repository_syncs", ["repo_full_name"])


def downgrade() -> None:
    op.drop_index("ix_github_repository_syncs_repo_full_name", table_name="github_repository_syncs")
    op.drop_index("ix_github_repository_syncs_user_id", table_name="github_repository_syncs")
    op.drop_table("github_repository_syncs")
    op.drop_index("ix_github_connections_user_id", table_name="github_connections")
    op.drop_table("github_connections")
    op.drop_column("documents", "security_status")
