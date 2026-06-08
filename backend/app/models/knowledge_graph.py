"""Knowledge graph nodes and edges (PostgreSQL-backed; optional Neo4j sync)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from app.db.database import Base


class GraphNode(Base):
    __tablename__ = "graph_nodes"
    __table_args__ = (
        UniqueConstraint("user_id", "workspace_id", "name", "node_type", name="uq_graph_node_identity"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    workspace_id = Column(String(64), nullable=False, default="default", index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(512), nullable=False, index=True)
    node_type = Column(String(64), nullable=False, default="entity")
    metadata_json = Column("metadata", JSON().with_variant(JSONB, "postgresql"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GraphEdge(Base):
    __tablename__ = "graph_edges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    workspace_id = Column(String(64), nullable=False, default="default", index=True)
    source_node_id = Column(Integer, ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    target_node_id = Column(Integer, ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    relation_type = Column(String(128), nullable=False, default="related_to")
    weight = Column(Float, nullable=False, default=1.0)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    evidence = Column(Text, nullable=True)
    metadata_json = Column("metadata", JSON().with_variant(JSONB, "postgresql"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
