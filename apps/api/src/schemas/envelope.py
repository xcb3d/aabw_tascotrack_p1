from __future__ import annotations

from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

from apps.api.src.schemas.common import ErrorCode

BodyT = TypeVar("BodyT")


class ErrorEnvelope(BaseModel):
    status: Literal["error"] = "error"
    code: ErrorCode
    message: str
    requestId: str


class GenericEnvelope(BaseModel, Generic[BodyT]):
    status: Literal["success"] = "success"
    message: Literal["SUCCESS"] = "SUCCESS"
    body: BodyT
    requestId: str


class HealthBody(BaseModel):
    ok: bool
    documents: int
    chunks: int
    users: int
    openaiConfigured: bool
    retriever: dict[str, Any] = Field(default_factory=dict)


class HealthEnvelope(GenericEnvelope[HealthBody]):
    body: HealthBody
