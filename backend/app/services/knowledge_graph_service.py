"""Knowledge graph builder, search, and GraphRAG context."""

from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.app_settings import get_settings
from app.models.document_entity import DocumentEntity
from app.models.knowledge_graph import GraphEdge, GraphNode

logger = logging.getLogger(__name__)

_RELATION_PATTERN = re.compile(
    r"\b([A-Z][a-zA-Z0-9_\-\s]{2,60}?)\s+(works at|partners with|acquired|owns|reports to|located in|uses|competes with)\s+([A-Z][a-zA-Z0-9_\-\s]{2,60}?)\b"
)


def _get_or_create_node(
    db: Session,
    *,
    user_id: int,
    workspace_id: str,
    name: str,
    node_type: str,
    document_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> GraphNode:
    normalized_name = name.strip()[:512]
    node = (
        db.query(GraphNode)
        .filter(
            GraphNode.user_id == user_id,
            GraphNode.workspace_id == workspace_id,
            GraphNode.name == normalized_name,
            GraphNode.node_type == node_type,
        )
        .first()
    )
    if node:
        return node

    node = GraphNode(
        user_id=user_id,
        workspace_id=workspace_id,
        document_id=document_id,
        name=normalized_name,
        node_type=node_type,
        metadata_json=metadata or {},
    )
    db.add(node)
    db.flush()
    return node


def _extract_relations_from_text(text: str) -> list[tuple[str, str, str]]:
    relations: list[tuple[str, str, str]] = []
    for match in _RELATION_PATTERN.finditer(text or ""):
        source, relation, target = match.group(1).strip(), match.group(2).strip(), match.group(3).strip()
        if source and target:
            relations.append((source, relation.replace(" ", "_"), target))
    return relations


def build_workspace_graph(
    db: Session,
    *,
    user_id: int,
    workspace_id: str = "default",
    document_id: int | None = None,
) -> dict[str, int]:
    """Build graph nodes/edges from document_entities and co-occurrence heuristics."""
    query = db.query(DocumentEntity).filter(DocumentEntity.user_id == user_id)
    if document_id is not None:
        query = query.filter(DocumentEntity.document_id == document_id)
    entities = query.all()

    nodes_created = 0
    edges_created = 0
    doc_entities: dict[int, list[DocumentEntity]] = {}
    for entity in entities:
        doc_entities.setdefault(entity.document_id, []).append(entity)

    for doc_id, doc_group in doc_entities.items():
        node_ids: list[int] = []
        for entity in doc_group:
            before = db.query(GraphNode).count()
            node = _get_or_create_node(
                db,
                user_id=user_id,
                workspace_id=workspace_id,
                name=entity.name,
                node_type=entity.entity_type or "entity",
                document_id=doc_id,
                metadata={"mentions": entity.mentions},
            )
            if db.query(GraphNode).count() > before:
                nodes_created += 1
            node_ids.append(node.id)

            for source, relation, target in _extract_relations_from_text(entity.context or ""):
                src = _get_or_create_node(
                    db, user_id=user_id, workspace_id=workspace_id, name=source, node_type="entity", document_id=doc_id
                )
                tgt = _get_or_create_node(
                    db, user_id=user_id, workspace_id=workspace_id, name=target, node_type="entity", document_id=doc_id
                )
                db.add(
                    GraphEdge(
                        user_id=user_id,
                        workspace_id=workspace_id,
                        source_node_id=src.id,
                        target_node_id=tgt.id,
                        relation_type=relation,
                        document_id=doc_id,
                        evidence=entity.context,
                    )
                )
                edges_created += 1

        # Co-occurrence edges within same document.
        for i, left_id in enumerate(node_ids):
            for right_id in node_ids[i + 1 : i + 4]:
                if left_id == right_id:
                    continue
                db.add(
                    GraphEdge(
                        user_id=user_id,
                        workspace_id=workspace_id,
                        source_node_id=left_id,
                        target_node_id=right_id,
                        relation_type="co_occurs_in_document",
                        document_id=doc_id,
                        weight=0.5,
                    )
                )
                edges_created += 1

    db.commit()
    _maybe_sync_neo4j(db, user_id=user_id, workspace_id=workspace_id)
    return {"nodes_created": nodes_created, "edges_created": edges_created, "entity_rows": len(entities)}


def _maybe_sync_neo4j(db: Session, *, user_id: int, workspace_id: str) -> None:
    settings = get_settings()
    if not settings.NEO4J_URI:
        return
    try:
        from neo4j import GraphDatabase  # type: ignore[import-untyped]

        driver = GraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))
        nodes = (
            db.query(GraphNode)
            .filter(GraphNode.user_id == user_id, GraphNode.workspace_id == workspace_id)
            .all()
        )
        edges = (
            db.query(GraphEdge)
            .filter(GraphEdge.user_id == user_id, GraphEdge.workspace_id == workspace_id)
            .all()
        )
        with driver.session() as session:
            for node in nodes:
                session.run(
                    "MERGE (n:Entity {id: $id, user_id: $user_id, name: $name, type: $type})",
                    id=node.id,
                    user_id=user_id,
                    name=node.name,
                    type=node.node_type,
                )
            for edge in edges:
                session.run(
                    """
                    MATCH (a:Entity {id: $source_id}), (b:Entity {id: $target_id})
                    MERGE (a)-[r:REL {type: $relation}]->(b)
                    """,
                    source_id=edge.source_node_id,
                    target_id=edge.target_node_id,
                    relation=edge.relation_type,
                )
        driver.close()
    except Exception:
        logger.exception("Neo4j sync skipped due to error")


def search_graph(
    db: Session,
    *,
    user_id: int,
    query: str,
    workspace_id: str = "default",
    limit: int = 20,
) -> dict[str, Any]:
    needle = (query or "").strip().lower()
    if not needle:
        return {"nodes": [], "edges": []}

    nodes = (
        db.query(GraphNode)
        .filter(
            GraphNode.user_id == user_id,
            GraphNode.workspace_id == workspace_id,
            GraphNode.name.ilike(f"%{needle}%"),
        )
        .limit(limit)
        .all()
    )
    node_ids = [node.id for node in nodes]
    edges = (
        db.query(GraphEdge)
        .filter(
            GraphEdge.user_id == user_id,
            GraphEdge.workspace_id == workspace_id,
            or_(
                GraphEdge.source_node_id.in_(node_ids),
                GraphEdge.target_node_id.in_(node_ids),
            ),
        )
        .limit(limit * 2)
        .all()
        if node_ids
        else []
    )

    return {
        "nodes": [_serialize_node(node) for node in nodes],
        "edges": [_serialize_edge(edge) for edge in edges],
    }


def get_document_graph(db: Session, *, user_id: int, document_id: int) -> dict[str, Any]:
    nodes = (
        db.query(GraphNode)
        .filter(GraphNode.user_id == user_id, GraphNode.document_id == document_id)
        .all()
    )
    node_ids = [node.id for node in nodes]
    edges = (
        db.query(GraphEdge)
        .filter(
            GraphEdge.user_id == user_id,
            GraphEdge.document_id == document_id,
        )
        .all()
        if node_ids
        else []
    )
    return {
        "document_id": document_id,
        "nodes": [_serialize_node(node) for node in nodes],
        "edges": [_serialize_edge(edge) for edge in edges],
    }


def get_global_graph(
    db: Session,
    *,
    user_id: int,
    workspace_id: str = "default",
    limit: int = 100,
) -> dict[str, Any]:
    nodes = (
        db.query(GraphNode)
        .filter(GraphNode.user_id == user_id, GraphNode.workspace_id == workspace_id)
        .order_by(GraphNode.updated_at.desc())
        .limit(limit)
        .all()
    )
    node_ids = [node.id for node in nodes]
    edges = (
        db.query(GraphEdge)
        .filter(
            GraphEdge.user_id == user_id,
            GraphEdge.workspace_id == workspace_id,
            GraphEdge.source_node_id.in_(node_ids),
        )
        .limit(limit * 2)
        .all()
        if node_ids
        else []
    )
    return {"workspace_id": workspace_id, "nodes": [_serialize_node(n) for n in nodes], "edges": [_serialize_edge(e) for e in edges]}


def graph_rag_context(
    db: Session,
    *,
    user_id: int,
    query: str,
    workspace_id: str = "default",
    limit: int = 8,
) -> str:
    """Return graph neighborhood text for RAG prompts."""
    from app.services.redis_cache_service import cache_query_result, get_query_cache

    cache_key = f"{workspace_id}|{limit}|{query}"
    cached = get_query_cache("graph_rag", cache_key, user_id)
    if cached is not None:
        return cached

    import networkx as nx

    graph_data = get_global_graph(db, user_id=user_id, workspace_id=workspace_id, limit=200)
    if not graph_data["nodes"]:
        return ""

    g = nx.Graph()
    for node in graph_data["nodes"]:
        g.add_node(node["id"], label=node["name"], type=node["node_type"])
    for edge in graph_data["edges"]:
        g.add_edge(edge["source"], edge["target"], relation=edge["relation_type"])

    query_tokens = {token for token in re.findall(r"[a-z0-9]+", query.lower()) if len(token) > 2}
    scored: list[tuple[int, dict]] = []
    for node in graph_data["nodes"]:
        name_tokens = set(re.findall(r"[a-z0-9]+", node["name"].lower()))
        score = len(query_tokens & name_tokens)
        if score:
            scored.append((score, node))
    scored.sort(key=lambda item: item[0], reverse=True)
    selected = [node for _, node in scored[:limit]]
    if not selected:
        selected = graph_data["nodes"][:limit]

    lines = ["Knowledge graph context:"]
    for node in selected:
        neighbors = list(g.neighbors(node["id"]))[:4]
        neighbor_labels = []
        for neighbor_id in neighbors:
            neighbor = next((n for n in graph_data["nodes"] if n["id"] == neighbor_id), None)
            if neighbor:
                relation = g.edges.get((node["id"], neighbor_id), g.edges.get((neighbor_id, node["id"]), {})).get(
                    "relation", "related_to"
                )
                neighbor_labels.append(f"{relation} → {neighbor['name']}")
        line = f"- {node['name']} ({node['node_type']})"
        if neighbor_labels:
            line += ": " + "; ".join(neighbor_labels)
        lines.append(line)
    result = "\n".join(lines)
    cache_query_result("graph_rag", cache_key, user_id, result)
    return result


def _serialize_node(node: GraphNode) -> dict[str, Any]:
    return {
        "id": node.id,
        "name": node.name,
        "node_type": node.node_type,
        "document_id": node.document_id,
        "metadata": node.metadata_json or {},
    }


def _serialize_edge(edge: GraphEdge) -> dict[str, Any]:
    return {
        "id": edge.id,
        "source": edge.source_node_id,
        "target": edge.target_node_id,
        "relation_type": edge.relation_type,
        "weight": edge.weight,
        "document_id": edge.document_id,
        "evidence": edge.evidence,
    }
