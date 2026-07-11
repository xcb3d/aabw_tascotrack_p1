from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from apps.api.src.schemas.common import ActionStatus
from apps.api.src.schemas.envelope import GenericEnvelope


class ActionPreview(BaseModel):
    actionId: UUID
    actionType: str
    status: ActionStatus
    summary: str
    parameters: dict[str, Any] | None = None
    impact: str | None = None
    expiresAt: datetime
    confirmationToken: str | None = Field(default=None, exclude=True)


class ActionEnvelope(GenericEnvelope[ActionPreview]):
    body: ActionPreview


class ConfirmActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmationToken: str = Field(min_length=20)
    stepUpToken: str | None = Field(default=None, exclude=True)
