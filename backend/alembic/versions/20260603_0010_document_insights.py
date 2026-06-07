"""Add document_insights table for persisted document intelligence."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260603_0010"
down_revision: Union[str, None] = "20260602_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_insights",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("document_id", name="uq_document_insights_document_id"),
    )
    op.create_index("ix_document_insights_id", "document_insights", ["id"])
    op.create_index("ix_document_insights_document_id", "document_insights", ["document_id"])
    op.create_index("ix_document_insights_user_id", "document_insights", ["user_id")


def downgrade() -> None:
    op.drop_index("ix_document_insights_user_id", table_name="document_insights")
    op.drop_index("ix_document_insights_document_id", table_name="document_insights")
    op.drop_index("ix_document_insights_id", table_name="document_insights")
    op.drop_table("document_insights")
