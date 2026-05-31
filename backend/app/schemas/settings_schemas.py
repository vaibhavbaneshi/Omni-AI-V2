"""Pydantic schemas for workspace settings endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ProfileUpdateRequest(BaseModel):
    first_name: str = Field(default="", max_length=80)
    last_name: str = Field(default="", max_length=80)
    email: str = Field(..., min_length=3, max_length=255)
    bio: str = Field(default="", max_length=4000)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if "@" not in cleaned or cleaned.startswith("@") or cleaned.endswith("@"):
            raise ValueError("Invalid email address.")
        return cleaned

    @field_validator("first_name", "last_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip()


class PasswordChangeRequest(BaseModel):
    current_password: str | None = Field(default=None, max_length=256)
    new_password: str = Field(..., min_length=8, max_length=256)
    confirm_password: str = Field(..., min_length=8, max_length=256)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, value: str, info):
        new_password = info.data.get("new_password")
        if new_password and value != new_password:
            raise ValueError("Passwords do not match.")
        return value


class PreferencesUpdateRequest(BaseModel):
    default_model: str = Field(default="auto", max_length=80)
    response_style: str = Field(default="balanced", pattern="^(concise|balanced|detailed)$")
    system_prompt: str = Field(default="", max_length=4000)
    web_search_enabled: bool = True
    code_execution_enabled: bool = False
    streaming_enabled: bool = True
    theme: str = Field(default="dark", pattern="^(dark|light|system)$")
    font_size: str = Field(default="medium", pattern="^(small|medium|large)$")
    compact_mode: bool = False
    email_notifications: bool = True
    product_updates: bool = True
    usage_alerts: bool = True


class TwoFactorEnableRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=8)


class TwoFactorDisableRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=8)
    password: str | None = Field(default=None, max_length=256)


class WebhookUpdateRequest(BaseModel):
    url: str = Field(default="", max_length=500)
    events: list[str] = Field(default_factory=list)
    enabled: bool = False

    @field_validator("url")
    @classmethod
    def valid_webhook_url(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned and not cleaned.startswith(("https://", "http://localhost", "http://127.0.0.1")):
            raise ValueError("Webhook URL must use HTTPS.")
        return cleaned

    @field_validator("events")
    @classmethod
    def limit_events(cls, value: list[str]) -> list[str]:
        if len(value) > 20:
            raise ValueError("Too many webhook events.")
        return [item[:80] for item in value]


class BillingPlanRequest(BaseModel):
    plan: str = Field(..., pattern="^(free|pro)$")


class AccountDeleteRequest(BaseModel):
    confirmation: str = Field(..., min_length=1, max_length=64)
