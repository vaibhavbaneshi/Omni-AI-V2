"""Add RQ job id column for durable ingestion tracking."""

from alembic import op
import sqlalchemy as sa

revision = "20260601_0008"
down_revision = "20260531_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("indexing_job_id", sa.String(length=128), nullable=True))
    op.create_index("ix_documents_indexing_job_id", "documents", ["indexing_job_id"])


def downgrade() -> None:
    op.drop_index("ix_documents_indexing_job_id", table_name="documents")
    op.drop_column("documents", "indexing_job_id")
