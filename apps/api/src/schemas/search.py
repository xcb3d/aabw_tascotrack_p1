from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apps.api.src.schemas.common import Classification
from apps.api.src.schemas.envelope import GenericEnvelope
from apps.api.src.schemas.page import PageInfo


class SearchFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    department: str | None = None
    classification: Classification | None = None


class SearchPageRequest(BaseModel):
    pageSize: int = Field(default=10, ge=1, le=20)
    currentPage: int = Field(default=0, ge=0)


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=8000)
    filters: SearchFilters | None = None
    pageInfo: SearchPageRequest | None = None


class SearchHit(BaseModel):
    documentId: str
    chunkId: str
    title: str
    department: str
    classification: Classification
    section: str
    snippet: str
    score: float = Field(ge=0, le=1)
    allowedReason: str | None = None
    piiTypes: list[str] | None = None


class SearchBody(BaseModel):
    result: list[SearchHit] | None = None
    pageInfo: PageInfo | None = None
    permissionDecision: str | None = None
    likelyPermissionDenied: bool | None = None
    deniedMatchCount: int | None = None
    dlp: dict[str, Any] | None = None
    roleIdentifier: dict[str, Any] | None = None


class SearchEnvelope(GenericEnvelope[SearchBody]):
    body: SearchBody
