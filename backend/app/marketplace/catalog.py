"""Agent marketplace — templates, installs, versioning."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.agents.lifecycle import create_agent, serialize_agent
from app.models.marketplace import MarketplaceInstall, MarketplaceTemplate, MarketplaceTemplateVersion

BUILTIN_TEMPLATES: list[dict[str, Any]] = [
    {
        "slug": "research-agent",
        "name": "Research Agent",
        "category": "research",
        "description": "Plans, searches, retrieves, synthesizes, and cites sources.",
        "config": {"agent_type": "research", "schedule_kind": "daily", "config": {"max_iterations": 3}},
    },
    {
        "slug": "code-review-agent",
        "name": "Code Review Agent",
        "category": "engineering",
        "description": "Reviews code changes and highlights risks and improvements.",
        "config": {
            "agent_type": "custom",
            "config": {
                "prompt": "You are a senior code reviewer. Analyze code for bugs, security issues, and maintainability.",
            },
        },
    },
    {
        "slug": "security-audit-agent",
        "name": "Security Audit Agent",
        "category": "security",
        "description": "Performs security-focused analysis on documents and repositories.",
        "config": {
            "agent_type": "custom",
            "config": {"prompt": "You are a security auditor. Identify vulnerabilities, misconfigurations, and compliance gaps."},
        },
    },
    {
        "slug": "document-monitor-agent",
        "name": "Document Monitor",
        "category": "operations",
        "description": "Monitors uploaded documents for stale embeddings and re-index needs.",
        "config": {"agent_type": "document_monitor", "schedule_kind": "daily", "config": {"stale_days": 14}},
    },
    {
        "slug": "github-monitor-agent",
        "name": "GitHub Monitor",
        "category": "connectors",
        "description": "Watches GitHub repositories for changes and syncs updates.",
        "config": {"agent_type": "github_monitor", "schedule_kind": "daily", "config": {}},
    },
    {
        "slug": "product-manager-agent",
        "name": "Product Manager Agent",
        "category": "product",
        "description": "Turns feedback and docs into prioritized product insights.",
        "config": {
            "agent_type": "custom",
            "config": {"prompt": "You are a product manager. Synthesize user feedback into themes, priorities, and roadmap suggestions."},
        },
    },
    {
        "slug": "technical-writer-agent",
        "name": "Technical Writer Agent",
        "category": "content",
        "description": "Drafts documentation from workspace sources.",
        "config": {
            "agent_type": "custom",
            "config": {"prompt": "You are a technical writer. Produce clear documentation with structure and examples."},
        },
    },
    {
        "slug": "meeting-summary-agent",
        "name": "Meeting Summary Agent",
        "category": "productivity",
        "description": "Summarizes meeting notes into action items and decisions.",
        "config": {
            "agent_type": "custom",
            "config": {"prompt": "Summarize meetings into decisions, action items, and owners."},
        },
    },
    {
        "slug": "knowledge-graph-agent",
        "name": "Knowledge Graph Agent",
        "category": "knowledge",
        "description": "Builds and maintains knowledge graph insights from documents.",
        "config": {
            "agent_type": "custom",
            "config": {"prompt": "Extract entities and relationships to enrich the workspace knowledge graph."},
        },
    },
]


def seed_marketplace_templates(db: Session) -> int:
    created = 0
    for item in BUILTIN_TEMPLATES:
        existing = db.query(MarketplaceTemplate).filter(MarketplaceTemplate.slug == item["slug"]).first()
        if existing:
            continue
        template = MarketplaceTemplate(
            slug=item["slug"],
            name=item["name"],
            description=item["description"],
            category=item["category"],
            config=item["config"],
            is_public=True,
            current_version="1.0.0",
        )
        db.add(template)
        db.flush()
        db.add(
            MarketplaceTemplateVersion(
                template_id=template.id,
                version="1.0.0",
                config=item["config"],
                changelog="Initial release",
            )
        )
        created += 1
    db.commit()
    return created


def list_templates(db: Session, *, query: str | None = None, category: str | None = None, limit: int = 100) -> list[MarketplaceTemplate]:
    q = db.query(MarketplaceTemplate).filter(MarketplaceTemplate.is_public.is_(True))
    if category:
        q = q.filter(MarketplaceTemplate.category == category)
    if query:
        like = f"%{query.strip()}%"
        q = q.filter(MarketplaceTemplate.name.ilike(like) | MarketplaceTemplate.description.ilike(like))
    return q.order_by(MarketplaceTemplate.install_count.desc()).limit(limit).all()


def get_template(db: Session, *, slug: str) -> MarketplaceTemplate | None:
    return db.query(MarketplaceTemplate).filter(MarketplaceTemplate.slug == slug).first()


def install_template(db: Session, *, user_id: int, slug: str, name: str | None = None) -> dict[str, Any]:
    template = get_template(db, slug=slug)
    if not template:
        raise ValueError(f"Template '{slug}' not found.")
    existing = (
        db.query(MarketplaceInstall)
        .filter(MarketplaceInstall.user_id == user_id, MarketplaceInstall.template_id == template.id)
        .first()
    )
    if existing and existing.agent_id:
        from app.models.autonomous_agent import AutonomousAgent

        agent = db.query(AutonomousAgent).filter(AutonomousAgent.id == existing.agent_id).first()
        return {"install_id": existing.id, "agent": serialize_agent(agent) if agent else None, "already_installed": True}

    cfg = template.config or {}
    agent = create_agent(
        db,
        user_id=user_id,
        name=name or template.name,
        agent_type=cfg.get("agent_type", "custom"),
        description=template.description,
        config=cfg.get("config") or {},
        schedule_kind=cfg.get("schedule_kind", "manual"),
        schedule_config=cfg.get("schedule_config") or {},
        template_id=template.id,
    )
    if existing:
        existing.agent_id = agent.id
        existing.installed_version = template.current_version
    else:
        db.add(
            MarketplaceInstall(
                user_id=user_id,
                template_id=template.id,
                agent_id=agent.id,
                installed_version=template.current_version,
            )
        )
    template.install_count = (template.install_count or 0) + 1
    db.commit()
    return {"install_id": None, "agent": serialize_agent(agent), "already_installed": False}


def toggle_favorite(db: Session, *, user_id: int, slug: str, favorited: bool) -> bool:
    template = get_template(db, slug=slug)
    if not template:
        return False
    install = (
        db.query(MarketplaceInstall)
        .filter(MarketplaceInstall.user_id == user_id, MarketplaceInstall.template_id == template.id)
        .first()
    )
    if not install:
        install = MarketplaceInstall(
            user_id=user_id,
            template_id=template.id,
            agent_id=None,
            installed_version=template.current_version,
            favorited=favorited,
        )
        db.add(install)
    else:
        install.favorited = favorited
    db.commit()
    return True


def serialize_template(row: MarketplaceTemplate, *, favorited: bool = False) -> dict[str, Any]:
    return {
        "id": row.id,
        "slug": row.slug,
        "name": row.name,
        "description": row.description,
        "category": row.category,
        "current_version": row.current_version,
        "install_count": row.install_count,
        "favorited": favorited,
        "config_preview": {
            "agent_type": (row.config or {}).get("agent_type"),
            "schedule_kind": (row.config or {}).get("schedule_kind"),
        },
    }
