"""Versioned configuration for the internal embedding model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ClassificationAction = Literal["embed_internal", "block"]


class EmbeddingModelConfig(BaseModel):
    """Validated model-registry entry used by ingestion and query embedding."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    model_id: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    execution: Literal["internal_only"]
    native_dimension: int = Field(gt=0, le=2_000)
    output_dimension: int = Field(gt=0, le=2_000)
    max_input_tokens: int = Field(gt=0)
    normalize: Literal[True]
    distance: Literal["cosine"]
    storage_type: Literal["halfvec", "vector"]
    query_instruction: str = Field(min_length=1)
    document_instruction: str | None = None
    classification_policy: dict[str, ClassificationAction]

    @model_validator(mode="after")
    def validate_security_and_dimension(self) -> "EmbeddingModelConfig":
        if self.output_dimension > self.native_dimension:
            raise ValueError("output_dimension cannot exceed native_dimension")
        expected = {"Public", "Internal", "Confidential", "Restricted", "Secret"}
        if set(self.classification_policy) != expected:
            raise ValueError("classification_policy must define the complete taxonomy")
        if self.classification_policy["Secret"] != "block":
            raise ValueError("Secret content must never be embedded")
        if any(
            self.classification_policy[item] != "embed_internal"
            for item in ("Public", "Internal", "Confidential", "Restricted")
        ):
            raise ValueError("all indexable classifications must use internal embeddings")
        return self

    @property
    def is_production_pinned(self) -> bool:
        return self.revision != "PIN_BEFORE_PRODUCTION"


def load_embedding_config(path: str | Path) -> EmbeddingModelConfig:
    """Load a registry entry without downloading or executing model code."""

    value = json.loads(Path(path).read_text(encoding="utf-8"))
    return EmbeddingModelConfig.model_validate(value)
