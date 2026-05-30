"""Workspace settings — profile, security, preferences, API keys, billing."""

from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pyotp
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.app_settings import get_settings
from app.models.user import User
from app.models.user_settings import (
    BillingInvoice,
    BillingSubscription,
    UserApiKey,
    UserPreference,
    UserSessionRecord,
    UserWebhook,
)
from app.services.analytics_service import get_user_overview
from app.services.auth_service import hash_password, verify_password

AVATAR_DIR = Path("uploads/avatars")
PLAN_PRICES = {"free": 0, "pro": 2000}
WEBHOOK_EVENTS = {"message.created", "chat.completed", "error.occurred"}


def _now() -> datetime:
    return datetime.utcnow()


def _display_name(user: User) -> str:
    parts = [user.first_name or "", user.last_name or ""]
    cleaned = " ".join(part.strip() for part in parts if part and part.strip())
    if cleaned:
        return cleaned
    return user.email.split("@")[0]


def device_label_from_user_agent(user_agent: str | None) -> str:
    ua = (user_agent or "").lower()
    if "iphone" in ua:
        return "iPhone"
    if "ipad" in ua:
        return "iPad"
    if "android" in ua:
        return "Android"
    if "mac os" in ua or "macintosh" in ua:
        return "Mac"
    if "windows" in ua:
        return "Windows"
    if "linux" in ua:
        return "Linux"
    return "Web browser"


def ensure_user_settings(db: Session, user: User) -> None:
    if not user.created_at:
        user.created_at = _now()
        user.updated_at = _now()

    if user.has_password is None:
        user.has_password = not bool(user.oauth_provider)

    if not db.query(UserPreference).filter(UserPreference.user_id == user.id).first():
        db.add(UserPreference(user_id=user.id))

    if not db.query(BillingSubscription).filter(BillingSubscription.user_id == user.id).first():
        db.add(
            BillingSubscription(
                user_id=user.id,
                plan="free",
                status="active",
                amount_cents=0,
                billing_cycle="monthly",
            )
        )

    if not db.query(UserWebhook).filter(UserWebhook.user_id == user.id).first():
        db.add(UserWebhook(user_id=user.id, url="", events="[]", enabled=False))

    if not db.query(UserApiKey).filter(UserApiKey.user_id == user.id).first():
        _create_api_key_record(db, user)

    db.commit()


def register_user_session(
    db: Session,
    *,
    user: User,
    session_jti: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> UserSessionRecord:
    ensure_user_settings(db, user)
    record = UserSessionRecord(
        user_id=user.id,
        session_jti=session_jti,
        device_label=device_label_from_user_agent(user_agent),
        ip_address=ip_address,
        user_agent=(user_agent or "")[:500] or None,
        created_at=_now(),
        last_active_at=_now(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def touch_user_session(db: Session, *, user_id: int, session_jti: str | None) -> None:
    if not session_jti:
        return
    record = (
        db.query(UserSessionRecord)
        .filter(
            UserSessionRecord.user_id == user_id,
            UserSessionRecord.session_jti == session_jti,
            UserSessionRecord.revoked_at.is_(None),
        )
        .first()
    )
    if record:
        record.last_active_at = _now()
        db.commit()


def _preference_payload(preference: UserPreference) -> dict:
    return {
        "default_model": preference.default_model,
        "response_style": preference.response_style,
        "system_prompt": preference.system_prompt,
        "web_search_enabled": preference.web_search_enabled,
        "code_execution_enabled": preference.code_execution_enabled,
        "streaming_enabled": preference.streaming_enabled,
        "theme": preference.theme,
        "font_size": preference.font_size,
        "compact_mode": preference.compact_mode,
        "email_notifications": preference.email_notifications,
        "product_updates": preference.product_updates,
        "usage_alerts": preference.usage_alerts,
    }


def _webhook_payload(webhook: UserWebhook) -> dict:
    try:
        events = json.loads(webhook.events or "[]")
    except json.JSONDecodeError:
        events = []
    return {
        "url": webhook.url or "",
        "events": events,
        "enabled": bool(webhook.enabled),
    }


def _api_key_payload(api_key: UserApiKey | None) -> dict:
    if not api_key:
        return {"prefix": None, "created_at": None, "last_used_at": None, "active": False}
    return {
        "prefix": api_key.key_prefix,
        "created_at": api_key.created_at.isoformat() if api_key.created_at else None,
        "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
        "active": True,
    }


def _billing_payload(db: Session, user: User, subscription: BillingSubscription) -> dict:
    overview = get_user_overview(db, user_id=user.id, days=30)
    ai = overview.get("ai", {})
    rag = overview.get("rag", {})
    users = overview.get("users", {})

    message_limit = 50000 if subscription.plan == "pro" else 5000
    api_limit = 100000 if subscription.plan == "pro" else 10000
    storage_limit_gb = 10 if subscription.plan == "pro" else 1

    messages_used = int(users.get("messages") or 0)
    api_used = int(users.get("api_requests") or 0)
    uploads = int(rag.get("uploads") or 0)
    storage_used_gb = round(uploads * 0.05, 2)

    invoices = (
        db.query(BillingInvoice)
        .filter(BillingInvoice.user_id == user.id)
        .order_by(BillingInvoice.invoice_date.desc())
        .limit(12)
        .all()
    )

    if subscription.plan == "pro" and not invoices:
        _seed_pro_invoices(db, user.id)
        invoices = (
            db.query(BillingInvoice)
            .filter(BillingInvoice.user_id == user.id)
            .order_by(BillingInvoice.invoice_date.desc())
            .limit(12)
            .all()
        )

    return {
        "plan": subscription.plan,
        "status": subscription.status,
        "amount_cents": subscription.amount_cents,
        "billing_cycle": subscription.billing_cycle,
        "next_billing_date": subscription.next_billing_date.isoformat()
        if subscription.next_billing_date
        else None,
        "payment_method_brand": subscription.payment_method_brand,
        "payment_method_last4": subscription.payment_method_last4,
        "cancel_at_period_end": subscription.cancel_at_period_end,
        "usage": {
            "messages": {
                "used": messages_used,
                "limit": message_limit,
                "percent": min(100, round((messages_used / message_limit) * 100)) if message_limit else 0,
            },
            "api_calls": {
                "used": api_used,
                "limit": api_limit,
                "percent": min(100, round((api_used / api_limit) * 100)) if api_limit else 0,
            },
            "storage_gb": {
                "used": storage_used_gb,
                "limit": storage_limit_gb,
                "percent": min(100, round((storage_used_gb / storage_limit_gb) * 100))
                if storage_limit_gb
                else 0,
            },
            "tokens": int(ai.get("total_tokens") or 0),
        },
        "invoices": [
            {
                "id": invoice.id,
                "date": invoice.invoice_date.strftime("%b %d, %Y") if invoice.invoice_date else "",
                "amount": f"${invoice.amount_cents / 100:.2f}",
                "amount_cents": invoice.amount_cents,
                "status": invoice.status,
                "description": invoice.description,
            }
            for invoice in invoices
        ],
    }


def _seed_pro_invoices(db: Session, user_id: int) -> None:
    today = _now()
    for months_ago in (0, 1, 2):
        invoice_date = today - timedelta(days=30 * months_ago)
        db.add(
            BillingInvoice(
                user_id=user_id,
                amount_cents=2000,
                status="paid",
                description="Pro Plan - Monthly",
                invoice_date=invoice_date,
            )
        )
    db.commit()


def get_workspace_settings(
    db: Session,
    user: User,
    *,
    current_session_jti: str | None = None,
) -> dict:
    ensure_user_settings(db, user)
    preference = db.query(UserPreference).filter(UserPreference.user_id == user.id).one()
    subscription = db.query(BillingSubscription).filter(BillingSubscription.user_id == user.id).one()
    webhook = db.query(UserWebhook).filter(UserWebhook.user_id == user.id).one()
    api_key = db.query(UserApiKey).filter(UserApiKey.user_id == user.id).first()
    sessions = (
        db.query(UserSessionRecord)
        .filter(UserSessionRecord.user_id == user.id, UserSessionRecord.revoked_at.is_(None))
        .order_by(UserSessionRecord.last_active_at.desc())
        .all()
    )

    settings = get_settings()
    return {
        "profile": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "bio": user.bio or "",
            "avatar_url": user.avatar_url,
            "display_name": _display_name(user),
            "oauth_provider": user.oauth_provider,
            "has_password": bool(user.has_password),
            "password_changed_at": user.password_changed_at.isoformat()
            if user.password_changed_at
            else None,
            "totp_enabled": bool(user.totp_enabled),
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "security": {
            "totp_enabled": bool(user.totp_enabled),
            "has_password": bool(user.has_password),
            "password_changed_at": user.password_changed_at.isoformat()
            if user.password_changed_at
            else None,
            "sessions": [
                {
                    "id": session.id,
                    "device_label": session.device_label,
                    "ip_address": session.ip_address,
                    "created_at": session.created_at.isoformat() if session.created_at else None,
                    "last_active_at": session.last_active_at.isoformat()
                    if session.last_active_at
                    else None,
                    "is_current": session.session_jti == current_session_jti,
                }
                for session in sessions
            ],
        },
        "preferences": _preference_payload(preference),
        "api": {
            "key": _api_key_payload(api_key),
            "rate_limits": {
                "requests_per_minute": settings.RATE_LIMIT_PER_MINUTE,
                "tokens_per_minute": 100_000,
                "max_upload_bytes": settings.MAX_UPLOAD_BYTES,
            },
            "webhook": _webhook_payload(webhook),
        },
        "billing": _billing_payload(db, user, subscription),
    }


def update_profile(db: Session, user: User, *, payload: dict) -> dict:
    ensure_user_settings(db, user)
    email = payload["email"].strip().lower()
    if email != user.email:
        existing = db.query(User).filter(User.email == email, User.id != user.id).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email is already in use.")

    user.first_name = payload.get("first_name", "").strip() or None
    user.last_name = payload.get("last_name", "").strip() or None
    user.email = email
    user.bio = payload.get("bio", "").strip() or None
    user.updated_at = _now()
    db.commit()
    db.refresh(user)
    return get_workspace_settings(db, user)["profile"]


def change_password(db: Session, user: User, *, payload: dict) -> dict:
    if user.has_password:
        current = payload.get("current_password") or ""
        if not current or not verify_password(current, user.password):
            raise HTTPException(status_code=400, detail="Current password is incorrect.")

    user.password = hash_password(payload["new_password"])
    user.has_password = True
    user.password_changed_at = _now()
    user.updated_at = _now()
    db.commit()
    return {"message": "Password updated successfully."}


def begin_two_factor_setup(db: Session, user: User) -> dict:
    if user.totp_enabled:
        raise HTTPException(status_code=400, detail="Two-factor authentication is already enabled.")

    secret = pyotp.random_base32()
    user.totp_secret = secret
    user.updated_at = _now()
    db.commit()

    issuer = get_settings().APP_NAME
    provisioning_uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=issuer)
    return {
        "secret": secret,
        "provisioning_uri": provisioning_uri,
        "issuer": issuer,
    }


def enable_two_factor(db: Session, user: User, *, code: str) -> dict:
    if not user.totp_secret:
        raise HTTPException(status_code=400, detail="Start 2FA setup before verifying a code.")

    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(code.strip(), valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid authentication code.")

    user.totp_enabled = True
    user.updated_at = _now()
    db.commit()
    return {"message": "Two-factor authentication enabled.", "totp_enabled": True}


def disable_two_factor(db: Session, user: User, *, code: str, password: str | None = None) -> dict:
    if not user.totp_enabled or not user.totp_secret:
        raise HTTPException(status_code=400, detail="Two-factor authentication is not enabled.")

    if user.has_password:
        if not password or not verify_password(password, user.password):
            raise HTTPException(status_code=400, detail="Password is required to disable 2FA.")

    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(code.strip(), valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid authentication code.")

    user.totp_enabled = False
    user.totp_secret = None
    user.updated_at = _now()
    db.commit()
    return {"message": "Two-factor authentication disabled.", "totp_enabled": False}


def list_sessions(db: Session, user: User, *, current_session_jti: str | None = None) -> list[dict]:
    ensure_user_settings(db, user)
    sessions = (
        db.query(UserSessionRecord)
        .filter(UserSessionRecord.user_id == user.id, UserSessionRecord.revoked_at.is_(None))
        .order_by(UserSessionRecord.last_active_at.desc())
        .all()
    )
    return [
        {
            "id": session.id,
            "device_label": session.device_label,
            "ip_address": session.ip_address,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "last_active_at": session.last_active_at.isoformat() if session.last_active_at else None,
            "is_current": session.session_jti == current_session_jti,
        }
        for session in sessions
    ]


def revoke_session(db: Session, user: User, session_id: int) -> dict:
    record = (
        db.query(UserSessionRecord)
        .filter(UserSessionRecord.id == session_id, UserSessionRecord.user_id == user.id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Session not found.")
    record.revoked_at = _now()
    db.commit()
    return {"message": "Session revoked."}


def revoke_other_sessions(db: Session, user: User, *, current_session_jti: str | None) -> dict:
    query = db.query(UserSessionRecord).filter(
        UserSessionRecord.user_id == user.id,
        UserSessionRecord.revoked_at.is_(None),
    )
    if current_session_jti:
        query = query.filter(UserSessionRecord.session_jti != current_session_jti)
    revoked = query.update({"revoked_at": _now()}, synchronize_session=False)
    db.commit()
    return {"message": f"Revoked {revoked} session(s).", "revoked": revoked}


def update_preferences(db: Session, user: User, *, payload: dict) -> dict:
    ensure_user_settings(db, user)
    preference = db.query(UserPreference).filter(UserPreference.user_id == user.id).one()
    for field, value in payload.items():
        setattr(preference, field, value)
    preference.updated_at = _now()
    db.commit()
    return _preference_payload(preference)


def _create_api_key_record(db: Session, user: User) -> tuple[UserApiKey, str]:
    raw_key = f"omni_{secrets.token_urlsafe(32)}"
    record = UserApiKey(
        user_id=user.id,
        key_prefix=f"{raw_key[:12]}...",
        key_hash=hash_password(raw_key),
        created_at=_now(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record, raw_key


def regenerate_api_key(db: Session, user: User) -> dict:
    ensure_user_settings(db, user)
    existing = db.query(UserApiKey).filter(UserApiKey.user_id == user.id).first()
    if existing:
        db.delete(existing)
        db.commit()
    record, raw_key = _create_api_key_record(db, user)
    return {
        "api_key": raw_key,
        "prefix": record.key_prefix,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "message": "API key regenerated. Copy it now — it won't be shown again.",
    }


def update_webhook(db: Session, user: User, *, payload: dict) -> dict:
    ensure_user_settings(db, user)
    webhook = db.query(UserWebhook).filter(UserWebhook.user_id == user.id).one()
    events = [event for event in payload.get("events", []) if event in WEBHOOK_EVENTS]
    webhook.url = (payload.get("url") or "").strip()
    webhook.events = json.dumps(events)
    webhook.enabled = bool(payload.get("enabled")) and bool(webhook.url)
    webhook.updated_at = _now()
    db.commit()
    return _webhook_payload(webhook)


def change_billing_plan(db: Session, user: User, *, plan: str) -> dict:
    ensure_user_settings(db, user)
    subscription = db.query(BillingSubscription).filter(BillingSubscription.user_id == user.id).one()
    subscription.plan = plan
    subscription.amount_cents = PLAN_PRICES[plan]
    subscription.status = "active"
    subscription.cancel_at_period_end = False
    subscription.updated_at = _now()

    if plan == "pro":
        subscription.payment_method_brand = subscription.payment_method_brand or "Visa"
        subscription.payment_method_last4 = subscription.payment_method_last4 or "4242"
        subscription.next_billing_date = _now() + timedelta(days=30)
        _seed_pro_invoices(db, user.id)
    else:
        subscription.payment_method_brand = None
        subscription.payment_method_last4 = None
        subscription.next_billing_date = None

    db.commit()
    return _billing_payload(db, user, subscription)


def cancel_subscription(db: Session, user: User) -> dict:
    ensure_user_settings(db, user)
    subscription = db.query(BillingSubscription).filter(BillingSubscription.user_id == user.id).one()
    if subscription.plan == "free":
        raise HTTPException(status_code=400, detail="You are already on the free plan.")
    subscription.cancel_at_period_end = True
    subscription.status = "active"
    subscription.updated_at = _now()
    db.commit()
    return {"message": "Subscription will cancel at the end of the billing period."}


def get_invoice_download(db: Session, user: User, invoice_id: int) -> dict:
    invoice = (
        db.query(BillingInvoice)
        .filter(BillingInvoice.id == invoice_id, BillingInvoice.user_id == user.id)
        .first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found.")

    return {
        "id": invoice.id,
        "filename": f"invoice-{invoice.id}.txt",
        "content": (
            f"OmniAI Invoice #{invoice.id}\n"
            f"Date: {invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else 'N/A'}\n"
            f"Description: {invoice.description}\n"
            f"Amount: ${invoice.amount_cents / 100:.2f}\n"
            f"Status: {invoice.status}\n"
        ),
    }


async def upload_avatar(db: Session, user: User, file: UploadFile) -> dict:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Avatar must be an image file.")

    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Avatar must be 2MB or smaller.")

    suffix = ".jpg"
    if file.content_type == "image/png":
        suffix = ".png"
    elif file.content_type == "image/gif":
        suffix = ".gif"
    elif file.content_type == "image/webp":
        suffix = ".webp"

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{user.id}-{uuid.uuid4().hex}{suffix}"
    path = AVATAR_DIR / filename
    path.write_bytes(content)

    settings = get_settings()
    base_url = settings.API_PUBLIC_URL.rstrip("/")
    user.avatar_url = f"{base_url}/uploads/avatars/{filename}"
    user.updated_at = _now()
    db.commit()
    return {"avatar_url": user.avatar_url}


def delete_account(db: Session, user: User, *, confirmation: str) -> dict:
    if confirmation.strip().lower() != "delete my account":
        raise HTTPException(
            status_code=400,
            detail="Type 'delete my account' to confirm account deletion.",
        )

    db.query(UserSessionRecord).filter(UserSessionRecord.user_id == user.id).delete()
    db.query(UserApiKey).filter(UserApiKey.user_id == user.id).delete()
    db.query(UserWebhook).filter(UserWebhook.user_id == user.id).delete()
    db.query(UserPreference).filter(UserPreference.user_id == user.id).delete()
    db.query(BillingInvoice).filter(BillingInvoice.user_id == user.id).delete()
    db.query(BillingSubscription).filter(BillingSubscription.user_id == user.id).delete()
    db.delete(user)
    db.commit()
    return {"message": "Account deleted."}
