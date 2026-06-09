"""Agent marketplace models — Phase P."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from app.db.database import Base


class MarketplaceTemplate(Base):
    __tablename__ = "marketplace_templates"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(128), nullable=False, unique=True)
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(64), nullable=False)
    config = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    is_public = Column(Boolean, nullable=False, default=True)
    author_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    current_version = Column(String(32), nullable=False, default="1.0.0")
    install_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MarketplaceTemplateVersion(Base):
    __tablename__ = "marketplace_template_versions"
    __table_args__ = (UniqueConstraint("template_id", "version", name="uq_marketplace_template_version"),)

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("marketplace_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(String(32), nullable=False)
    config = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    changelog = Column(Text, nullable=True)
    published_at = Column(DateTime, default=datetime.utcnow)


class MarketplaceInstall(Base):
    __tablename__ = "marketplace_installs"
    __table_args__ = (UniqueConstraint("user_id", "template_id", name="uq_marketplace_install_user_template"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("marketplace_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("autonomous_agents.id", ondelete="SET NULL"), nullable=True)
    installed_version = Column(String(32), nullable=False)
    favorited = Column(Boolean, nullable=False, default=False)
    installed_at = Column(DateTime, default=datetime.utcnow)
