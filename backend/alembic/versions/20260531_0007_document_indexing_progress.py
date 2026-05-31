"""Add indexing progress columns to documents table."""

from alembic import op
import sqlalchemy as sa

revision = "20260531_0007"
down_revision = "20260531_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("indexing_stage", sa.String(length=32), nullable=False, server_default="queued"),
    )
    op.add_column("documents", sa.Column("indexing_error", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("indexing_started_at", sa.DateTime(), nullable=True))
    op.add_column("documents", sa.Column("indexing_updated_at", sa.DateTime(), nullable=True))
    op.add_column(
        "documents",
        sa.Column("embeddings_completed", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("documents", "embeddings_completed")
    op.drop_column("documents", "indexing_updated_at")
    op.drop_column("documents", "indexing_started_at")
    op.drop_column("documents", "indexing_error")
    op.drop_column("documents", "indexing_stage")
