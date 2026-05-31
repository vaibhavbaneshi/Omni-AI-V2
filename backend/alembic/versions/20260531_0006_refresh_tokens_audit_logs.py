"""Add refresh token session fields and security audit logs."""

from alembic import op
import sqlalchemy as sa


revision = "20260531_0006"
down_revision = "20260531_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_sessions", sa.Column("refresh_token_hash", sa.String(), nullable=True))
    op.add_column("user_sessions", sa.Column("refresh_expires_at", sa.DateTime(), nullable=True))
    op.create_index(
        "ix_user_sessions_refresh_token_hash",
        "user_sessions",
        ["refresh_token_hash"],
    )
    op.create_table(
        "security_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True, index=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=False, index=True),
        sa.Column("detail", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_security_audit_logs_id", "security_audit_logs", ["id"])


def downgrade() -> None:
    op.drop_table("security_audit_logs")
    op.drop_index("ix_user_sessions_refresh_token_hash", table_name="user_sessions")
    op.drop_column("user_sessions", "refresh_expires_at")
    op.drop_column("user_sessions", "refresh_token_hash")
