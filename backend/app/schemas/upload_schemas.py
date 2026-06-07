"""Validated upload form parameters."""

from __future__ import annotations

from pydantic import BaseModel, Field


class UploadFormParams(BaseModel):
    workspace_id: str = Field(default="default", min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    collection_id: int | None = Field(default=None, gt=0)
    session_id: int | None = Field(default=None, gt=0)
