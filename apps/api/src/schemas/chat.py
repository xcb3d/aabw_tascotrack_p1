from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from apps.api.src.schemas.action import ActionPreview
from apps.api.src.schemas.common import (
    AgentMode,
    AgentRoute,
    Classification,
    Confidence,
    PermissionDecision,
    RunStatus,
)
from apps.api.src.schemas.envelope import GenericEnvelope


class LegacyChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=8000)
    conversationId: str | None = None
    mode: str = "knowledge"
    stream: bool = False


class Citation(BaseModel):
    evidenceId: str | None = None
    documentId: str
    version: str | None = None
    title: str
    section: str
    page: int | None = None
    classification: Classification


class LegacyChatBody(BaseModel):
    conversationId: str | None = None
    answer: str | None = None
    citations: list[Citation] | None = None
    permissionDecision: str | None = None
    confidence: str | None = None
    modelUsed: str | None = None
    redactionApplied: bool | None = None
    dlpCategories: list[str] | None = None
    retrieval: dict[str, Any] | None = None
    roleIdentifier: dict[str, Any] | None = None


class LegacyChatEnvelope(GenericEnvelope[LegacyChatBody]):
    body: LegacyChatBody


class CreateChatSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    locale: str = "vi-VN"
    title: str | None = Field(default=None, max_length=200)


class SessionBody(BaseModel):
    sessionId: UUID
    createdAt: datetime
    locale: str | None = None


class SessionEnvelope(GenericEnvelope[SessionBody]):
    body: SessionBody


class AgentRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sessionId: UUID
    message: str = Field(min_length=1, max_length=8000)
    locale: str = "vi-VN"
    mode: AgentMode = AgentMode.AUTO
    clientRequestId: UUID


class Claim(BaseModel):
    claimId: str
    text: str
    evidenceIds: list[str] = Field(min_length=1)


class AgentRun(BaseModel):
    runId: UUID
    traceId: UUID
    sessionId: UUID | None = None
    status: RunStatus
    route: AgentRoute | None = None
    answer: str | None = None
    claims: list[Claim] | None = None
    citations: list[Citation] | None = None
    action: ActionPreview | None = None
    permissionDecision: PermissionDecision | None = None
    confidence: Confidence | None = None
    degradedReason: str | None = None


class AgentRunEnvelope(GenericEnvelope[AgentRun]):
    body: AgentRun
