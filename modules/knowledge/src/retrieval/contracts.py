"""AIE1 index handoff and AIE2 retrieval score contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalScoreBreakdown:
    """Stable observability fields; ranks are one-based when present."""

    bm25_rank: int | None
    vector_rank: int | None
    fused_rank: int
    reranker_score: float | None
    bm25_score: float | None = None
    vector_similarity: float | None = None
    fused_score: float | None = None

    def __post_init__(self) -> None:
        for name in ("bm25_rank", "vector_rank", "fused_rank"):
            value = getattr(self, name)
            if value is not None and value < 1:
                raise ValueError(f"{name} must be one-based")
        if self.reranker_score is not None and not 0 <= self.reranker_score <= 1:
            raise ValueError("reranker_score must be normalized to [0, 1]")


@dataclass(frozen=True)
class RetrievalCandidate:
    tenant_id: str
    chunk_id: str
    document_id: str
    document_version_id: str
    classification: str
    content: str
    scores: RetrievalScoreBreakdown
