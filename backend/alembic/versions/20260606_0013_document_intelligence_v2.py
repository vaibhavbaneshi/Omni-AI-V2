"""Document intelligence v2 — timeline and entity tables."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260606_0013"
down_revision: Union[str, None] = "20260605_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_timeline",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("events", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("document_id", name="uq_document_timeline_document_id"),
    )
    op.create_index("ix_document_timeline_document_id", "document_timeline", ["document_id"])
    op.create_index("ix_document_timeline_user_id", "document_timeline", ["user_id"])

    op.create_table(
        "document_entities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False, server_default="unknown"),
        sa.Column("mentions", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_document_entities_document_id", "document_entities", ["document_id"])
    op.create_index("ix_document_entities_user_id", "document_entities", ["user_id"])
    op.create_index("ix_document_entities_name", "document_entities", ["name"])


def downgrade() -> None:
    op.drop_index("ix_document_entities_name", table_name="document_entities")
    op.drop_index("ix_document_entities_user_id", table_name="document_entities")
    op.drop_index("ix_document_entities_document_id", table_name="document_entities")
    op.drop_table("document_entities")
    op.drop_index("ix_document_timeline_user_id", table_name="document_timeline")
    op.drop_index("ix_document_timeline_document_id", table_name="document_timeline")
    op.drop_table("document_timeline")
