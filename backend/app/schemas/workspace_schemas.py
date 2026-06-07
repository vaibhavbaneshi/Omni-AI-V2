"""Pydantic schemas for workspace folders, collections, and search."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatFolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    workspace_id: str = "default"


class ChatFolderUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ChatFolderResponse(BaseModel):
    id: int
    name: str
    workspace_id: str
    session_count: int = 0
    created_at: str | None = None


class SessionOrganizationUpdate(BaseModel):
    is_pinned: bool | None = None
    folder_id: int | None = None
    clear_folder: bool = False


class CollectionUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class MoveDocumentRequest(BaseModel):
    collection_id: int


class SearchResultItem(BaseModel):
    type: str
    id: int
    title: str
    snippet: str = ""
    session_id: int | None = None
    document_id: int | None = None
    collection_id: int | None = None
    updated_at: str | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
    counts: dict[str, int]
