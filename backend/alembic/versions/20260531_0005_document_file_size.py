"""Add uploaded document file size."""

from alembic import op
import sqlalchemy as sa


revision = "20260531_0005"
down_revision = "20260525_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("documents", "file_size", server_default=None)


def downgrade() -> None:
    op.drop_column("documents", "file_size")
