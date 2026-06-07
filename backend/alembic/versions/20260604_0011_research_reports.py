"""Add research_reports table for persisted research agent artifacts."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260604_0011"
down_revision: Union[str, None] = "20260603_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "research_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("chat_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="processing"),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("report", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("traces", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_research_reports_id", "research_reports", ["id"])
    op.create_index("ix_research_reports_user_id", "research_reports", ["user_id"])
    op.create_index("ix_research_reports_session_id", "research_reports", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_research_reports_session_id", table_name="research_reports")
    op.drop_index("ix_research_reports_user_id", table_name="research_reports")
    op.drop_index("ix_research_reports_id", table_name="research_reports")
    op.drop_table("research_reports")
