"""Extended user profile columns and workspace settings tables."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    default_model = Column(String, nullable=False, server_default="auto")
    response_style = Column(String, nullable=False, server_default="balanced")
    system_prompt = Column(Text, nullable=False, server_default="")
    web_search_enabled = Column(Boolean, nullable=False, server_default="1")
    code_execution_enabled = Column(Boolean, nullable=False, server_default="0")
    streaming_enabled = Column(Boolean, nullable=False, server_default="1")
    theme = Column(String, nullable=False, server_default="dark")
    font_size = Column(String, nullable=False, server_default="medium")
    compact_mode = Column(Boolean, nullable=False, server_default="0")
    email_notifications = Column(Boolean, nullable=False, server_default="1")
    product_updates = Column(Boolean, nullable=False, server_default="1")
    usage_alerts = Column(Boolean, nullable=False, server_default="1")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserSessionRecord(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_jti = Column(String, unique=True, nullable=False, index=True)
    device_label = Column(String, nullable=False, server_default="Unknown device")
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)


class UserApiKey(Base):
    __tablename__ = "user_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    key_prefix = Column(String, nullable=False)
    key_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)


class UserWebhook(Base):
    __tablename__ = "user_webhooks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    url = Column(String, nullable=False, server_default="")
    events = Column(Text, nullable=False, server_default="[]")
    enabled = Column(Boolean, nullable=False, server_default="0")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BillingSubscription(Base):
    __tablename__ = "billing_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    plan = Column(String, nullable=False, server_default="free")
    status = Column(String, nullable=False, server_default="active")
    amount_cents = Column(Integer, nullable=False, server_default="0")
    billing_cycle = Column(String, nullable=False, server_default="monthly")
    next_billing_date = Column(DateTime, nullable=True)
    payment_method_brand = Column(String, nullable=True)
    payment_method_last4 = Column(String, nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=False, server_default="0")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BillingInvoice(Base):
    __tablename__ = "billing_invoices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount_cents = Column(Integer, nullable=False)
    status = Column(String, nullable=False, server_default="paid")
    description = Column(String, nullable=False)
    invoice_date = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="billing_invoices")
