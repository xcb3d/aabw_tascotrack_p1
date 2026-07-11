from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from apps.api.src.schemas.common import Classification


class CreateDocumentForm(BaseModel):
    """Form fields for multipart createDocument (excluding binary file)."""

    title: str = Field(min_length=1, max_length=300)
    departmentId: str
    classification: Classification
    allowedAccess: list[str] | None = None


class CreateDocumentVersionForm(BaseModel):
    """Form fields for multipart createDocumentVersion (excluding binary file)."""

    effectiveFrom: datetime | None = None
