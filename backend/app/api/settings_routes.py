"""Workspace settings routes — profile, security, preferences, API, billing."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.core.security import get_current_token_payload, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.settings_schemas import (
    AccountDeleteRequest,
    BillingPlanRequest,
    PasswordChangeRequest,
    PreferencesUpdateRequest,
    ProfileUpdateRequest,
    TwoFactorDisableRequest,
    TwoFactorEnableRequest,
    WebhookUpdateRequest,
)
from app.services.settings_service import (
    begin_two_factor_setup,
    cancel_subscription,
    change_billing_plan,
    change_password,
    delete_account,
    disable_two_factor,
    enable_two_factor,
    get_invoice_download,
    get_workspace_settings,
    regenerate_api_key,
    revoke_other_sessions,
    revoke_session,
    update_preferences,
    update_profile,
    update_webhook,
    upload_avatar,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def read_settings(
    current_user: User = Depends(get_current_user),
    token_payload: dict = Depends(get_current_token_payload),
    db: Session = Depends(get_db),
):
    return get_workspace_settings(
        db,
        current_user,
        current_session_jti=token_payload.get("jti"),
    )


@router.patch("/profile")
def patch_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_profile(db, current_user, payload=payload.model_dump())


@router.post("/avatar")
async def post_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await upload_avatar(db, current_user, file)


@router.post("/password")
def post_password_change(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return change_password(db, current_user, payload=payload.model_dump())


@router.get("/2fa/setup")
def get_two_factor_setup(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return begin_two_factor_setup(db, current_user)


@router.post("/2fa/enable")
def post_two_factor_enable(
    payload: TwoFactorEnableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return enable_two_factor(db, current_user, code=payload.code)


@router.post("/2fa/disable")
def post_two_factor_disable(
    payload: TwoFactorDisableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return disable_two_factor(
        db,
        current_user,
        code=payload.code,
        password=payload.password,
    )


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return revoke_session(db, current_user, session_id)


@router.post("/sessions/revoke-others")
def post_revoke_other_sessions(
    current_user: User = Depends(get_current_user),
    token_payload: dict = Depends(get_current_token_payload),
    db: Session = Depends(get_db),
):
    return revoke_other_sessions(
        db,
        current_user,
        current_session_jti=token_payload.get("jti"),
    )


@router.patch("/preferences")
def patch_preferences(
    payload: PreferencesUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_preferences(db, current_user, payload=payload.model_dump())


@router.post("/api-key/regenerate")
def post_regenerate_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return regenerate_api_key(db, current_user)


@router.put("/webhook")
def put_webhook(
    payload: WebhookUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_webhook(db, current_user, payload=payload.model_dump())


@router.post("/billing/plan")
def post_billing_plan(
    payload: BillingPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return change_billing_plan(db, current_user, plan=payload.plan)


@router.post("/billing/cancel")
def post_cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return cancel_subscription(db, current_user)


@router.get("/billing/invoices/{invoice_id}/download")
def download_invoice(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invoice = get_invoice_download(db, current_user, invoice_id)
    return PlainTextResponse(
        content=invoice["content"],
        headers={"Content-Disposition": f'attachment; filename="{invoice["filename"]}"'},
    )


@router.delete("/account")
def delete_user_account(
    payload: AccountDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return delete_account(db, current_user, confirmation=payload.confirmation)
