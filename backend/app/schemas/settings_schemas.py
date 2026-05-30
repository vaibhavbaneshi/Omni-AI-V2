"""Pydantic schemas for workspace settings endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ProfileUpdateRequest(BaseModel):
    first_name: str = Field(default="", max_length=80)
    last_name: str = Field(default="", max_length=80)
    email: str = Field(..., min_length=3, max_length=255)
    bio: str = Field(default="", max_length=4000)


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
    default_model: str = "auto"
    response_style: str = "balanced"
    system_prompt: str = ""
    web_search_enabled: bool = True
    code_execution_enabled: bool = False
    streaming_enabled: bool = True
    theme: str = "dark"
    font_size: str = "medium"
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
    url: str = ""
    events: list[str] = Field(default_factory=list)
    enabled: bool = False


class BillingPlanRequest(BaseModel):
    plan: str = Field(..., pattern="^(free|pro)$")


class AccountDeleteRequest(BaseModel):
    confirmation: str = Field(..., min_length=1, max_length=64)
