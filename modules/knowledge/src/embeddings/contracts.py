"""Storage-independent boundary for internal embedding inference."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class TextToEmbed:
    chunk_id: str
    tenant_id: str
    document_version_id: str
    content: str
    content_sha256: str
    classification: str


@dataclass(frozen=True)
class EmbeddingRecord:
    chunk_id: str
    tenant_id: str
    document_version_id: str
    model_id: str
    model_revision: str
    dimension: int
    normalized: bool
    values: tuple[float, ...]
    content_sha256: str

    def __post_init__(self) -> None:
        if len(self.values) != self.dimension:
            raise ValueError("embedding value count does not match dimension")
        if self.dimension <= 0:
            raise ValueError("embedding dimension must be positive")
        if not all(math.isfinite(value) for value in self.values):
            raise ValueError("embedding values must be finite")
        if self.normalized:
            norm = math.sqrt(math.fsum(value * value for value in self.values))
            if not math.isclose(norm, 1.0, rel_tol=1e-3, abs_tol=1e-3):
                raise ValueError("normalized embedding must have unit L2 norm")


class Embedder(Protocol):
    """AIE1-owned internal service; implementations must never call a hosted API."""

    async def embed_documents(self, items: Sequence[TextToEmbed]) -> tuple[EmbeddingRecord, ...]: ...

    async def embed_query(self, query: str, *, tenant_id: str) -> tuple[float, ...]: ...
