"""Add chat folders and session organization fields."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260605_0012"
down_revision: Union[str, None] = "20260604_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_folders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False, server_default="default"),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "workspace_id", "name", name="uq_chat_folders_user_workspace_name"),
    )
    op.create_index("ix_chat_folders_id", "chat_folders", ["id"])
    op.create_index("ix_chat_folders_user_id", "chat_folders", ["user_id"])

    op.add_column(
        "chat_sessions",
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "chat_sessions",
        sa.Column("folder_id", sa.Integer(), sa.ForeignKey("chat_folders.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_chat_sessions_is_pinned", "chat_sessions", ["is_pinned"])
    op.create_index("ix_chat_sessions_folder_id", "chat_sessions", ["folder_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_sessions_folder_id", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_is_pinned", table_name="chat_sessions")
    op.drop_column("chat_sessions", "folder_id")
    op.drop_column("chat_sessions", "is_pinned")
    op.drop_index("ix_chat_folders_user_id", table_name="chat_folders")
    op.drop_index("ix_chat_folders_id", table_name="chat_folders")
    op.drop_table("chat_folders")
