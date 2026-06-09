"""Agent marketplace API — Phase P."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.app_settings import get_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.marketplace.catalog import (
    get_template,
    install_template,
    list_templates,
    serialize_template,
    toggle_favorite,
)
from app.models.marketplace import MarketplaceInstall
from app.models.user import User

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


class InstallRequest(BaseModel):
    name: str | None = Field(default=None, max_length=256)


class FavoriteRequest(BaseModel):
    favorited: bool = True


def _require_marketplace() -> None:
    if not get_settings().ENABLE_AGENT_MARKETPLACE:
        raise HTTPException(status_code=403, detail="Agent marketplace is disabled.")


@router.get("/templates")
def browse_templates(
    q: str | None = None,
    category: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_marketplace()
    templates = list_templates(db, query=q, category=category)
    favorites = {
        row.template_id
        for row in db.query(MarketplaceInstall)
        .filter(MarketplaceInstall.user_id == current_user.id, MarketplaceInstall.favorited.is_(True))
        .all()
    }
    return {
        "templates": [serialize_template(row, favorited=row.id in favorites) for row in templates],
    }


@router.get("/templates/{slug}")
def read_template(slug: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_marketplace()
    template = get_template(db, slug=slug)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found.")
    favorited = (
        db.query(MarketplaceInstall)
        .filter(
            MarketplaceInstall.user_id == current_user.id,
            MarketplaceInstall.template_id == template.id,
            MarketplaceInstall.favorited.is_(True),
        )
        .first()
        is not None
    )
    return serialize_template(template, favorited=favorited)


@router.post("/templates/{slug}/install")
def install_agent_template(
    slug: str,
    body: InstallRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_marketplace()
    try:
        return install_template(db, user_id=current_user.id, slug=slug, name=body.name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/templates/{slug}/favorite")
def favorite_template(
    slug: str,
    body: FavoriteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_marketplace()
    if not toggle_favorite(db, user_id=current_user.id, slug=slug, favorited=body.favorited):
        raise HTTPException(status_code=404, detail="Template not found.")
    return {"favorited": body.favorited}
