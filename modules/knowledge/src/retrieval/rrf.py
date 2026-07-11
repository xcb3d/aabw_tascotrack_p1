"""Reciprocal-rank fusion used by the AIE2 hybrid retriever."""

from __future__ import annotations

from collections.abc import Sequence


def reciprocal_rank_fusion(
    bm25_ids: Sequence[str], vector_ids: Sequence[str], *, k: int = 60
) -> tuple[tuple[str, float, int | None, int | None], ...]:
    if k < 1:
        raise ValueError("RRF k must be positive")
    bm25_ranks = {chunk_id: rank for rank, chunk_id in enumerate(bm25_ids, 1)}
    vector_ranks = {chunk_id: rank for rank, chunk_id in enumerate(vector_ids, 1)}
    all_ids = set(bm25_ranks) | set(vector_ranks)
    rows = []
    for chunk_id in all_ids:
        bm25_rank = bm25_ranks.get(chunk_id)
        vector_rank = vector_ranks.get(chunk_id)
        score = 0.0
        if bm25_rank is not None:
            score += 1 / (k + bm25_rank)
        if vector_rank is not None:
            score += 1 / (k + vector_rank)
        rows.append((chunk_id, score, bm25_rank, vector_rank))
    rows.sort(key=lambda row: (-row[1], row[0]))
    return tuple(rows)
