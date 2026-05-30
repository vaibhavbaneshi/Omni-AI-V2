"""Add session_id to documents for per-chat upload isolation."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260525_0002"
down_revision: Union[str, None] = "20260525_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("session_id", sa.Integer(), nullable=True))
    op.create_index("ix_documents_session_id", "documents", ["session_id"])
    op.create_foreign_key(
        "fk_documents_session_id",
        "documents",
        "chat_sessions",
        ["session_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_documents_session_id", "documents", type_="foreignkey")
    op.drop_index("ix_documents_session_id", table_name="documents")
    op.drop_column("documents", "session_id")
