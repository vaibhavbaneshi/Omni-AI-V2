"""Knowledge graph, agent traces, and RBAC tables."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260606_0014"
down_revision: Union[str, None] = "20260606_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "graph_nodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False, server_default="default"),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("node_type", sa.String(length=64), nullable=False, server_default="entity"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "workspace_id", "name", "node_type", name="uq_graph_node_identity"),
    )
    op.create_index("ix_graph_nodes_user_id", "graph_nodes", ["user_id"])
    op.create_index("ix_graph_nodes_name", "graph_nodes", ["name"])

    op.create_table(
        "graph_edges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False, server_default="default"),
        sa.Column("source_node_id", sa.Integer(), sa.ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_node_id", sa.Integer(), sa.ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relation_type", sa.String(length=128), nullable=False, server_default="related_to"),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_graph_edges_user_id", "graph_edges", ["user_id"])
    op.create_index("ix_graph_edges_source_node_id", "graph_edges", ["source_node_id"])
    op.create_index("ix_graph_edges_target_node_id", "graph_edges", ["target_node_id"])

    op.create_table(
        "agent_traces",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="running"),
        sa.Column("planner_output", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("agent_steps", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("critic_output", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("final_response_preview", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_agent_traces_user_id", "agent_traces", ["user_id"])
    op.create_index("ix_agent_traces_session_id", "agent_traces", ["session_id"])

    op.create_table(
        "user_roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="viewer"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", name="uq_user_roles_user_id"),
    )
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_roles_user_id", table_name="user_roles")
    op.drop_table("user_roles")
    op.drop_index("ix_agent_traces_session_id", table_name="agent_traces")
    op.drop_index("ix_agent_traces_user_id", table_name="agent_traces")
    op.drop_table("agent_traces")
    op.drop_index("ix_graph_edges_target_node_id", table_name="graph_edges")
    op.drop_index("ix_graph_edges_source_node_id", table_name="graph_edges")
    op.drop_index("ix_graph_edges_user_id", table_name="graph_edges")
    op.drop_table("graph_edges")
    op.drop_index("ix_graph_nodes_name", table_name="graph_nodes")
    op.drop_index("ix_graph_nodes_user_id", table_name="graph_nodes")
    op.drop_table("graph_nodes")
