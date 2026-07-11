from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PublicEvaluationRequest(BaseModel):
    limit: int | None = Field(default=None, ge=1, le=50)


class CreateEvaluationRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    datasetId: str
    candidateConfigId: str | None = None
    baselineConfigId: str | None = None
