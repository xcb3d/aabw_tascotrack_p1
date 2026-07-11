"""ACL-filtered BM25 + dense-vector + RRF + reranker retrieval engine."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from modules.knowledge.src.embeddings.qwen3 import Qwen3Embedder
from modules.knowledge.src.retrieval.artifacts import ArtifactChunk, ArtifactIndex
from modules.knowledge.src.retrieval.bm25 import BM25Index
from modules.knowledge.src.retrieval.contracts import RetrievalScoreBreakdown
from modules.knowledge.src.retrieval.filters import RetrievalSubject, can_read_chunk
from modules.knowledge.src.retrieval.reranker import Qwen3Reranker
from modules.knowledge.src.retrieval.rrf import reciprocal_rank_fusion


@dataclass(frozen=True)
class HybridSearchHit:
    chunk: ArtifactChunk
    scores: RetrievalScoreBreakdown
    final_rank: int


class HybridRetriever:
    def __init__(
        self,
        index: ArtifactIndex,
        embedder: Qwen3Embedder,
        *,
        reranker: Qwen3Reranker | None = None,
        candidate_limit: int = 50,
        rrf_k: int = 60,
    ) -> None:
        if candidate_limit < 1:
            raise ValueError("candidate_limit must be positive")
        self.index = index
        self.embedder = embedder
        self.reranker = reranker
        self.candidate_limit = candidate_limit
        self.rrf_k = rrf_k
        self.bm25 = BM25Index([chunk.bm25_text for chunk in index.chunks])
        self.positions = {chunk.chunk_id: position for position, chunk in enumerate(index.chunks)}

    def _authorized_positions(
        self,
        subject: RetrievalSubject,
        *,
        department: str | None,
        classification: str | None,
    ) -> tuple[int, ...]:
        positions = []
        for position, chunk in enumerate(self.index.chunks):
            if department is not None and chunk.department != department:
                continue
            if classification is not None and chunk.classification != classification:
                continue
            if can_read_chunk(
                subject,
                tenant_id=chunk.tenant_id,
                department=chunk.department,
                classification=chunk.classification,
                allowed_access=chunk.allowed_access,
            ):
                positions.append(position)
        return tuple(positions)

    async def search(
        self,
        query: str,
        subject: RetrievalSubject,
        *,
        top_k: int = 8,
        department: str | None = None,
        classification: str | None = None,
    ) -> tuple[HybridSearchHit, ...]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        if top_k < 1 or top_k > self.candidate_limit:
            raise ValueError("top_k must be between 1 and candidate_limit")
        authorized = self._authorized_positions(
            subject, department=department, classification=classification
        )
        if not authorized:
            return ()

        bm25_scores = self.bm25.scores(query)
        bm25_order = sorted(authorized, key=lambda pos: (-bm25_scores[pos], pos))
        bm25_order = [pos for pos in bm25_order if bm25_scores[pos] > 0][
            : self.candidate_limit
        ]

        query_vector = np.asarray(
            await self.embedder.embed_query(query, tenant_id=subject.tenant_id), dtype=np.float32
        )
        if query_vector.shape != (self.index.dimension,):
            raise ValueError("query embedding dimension does not match the index")
        vector_scores = self.index.vectors @ query_vector
        vector_order = sorted(authorized, key=lambda pos: (-float(vector_scores[pos]), pos))[
            : self.candidate_limit
        ]

        bm25_ids = [self.index.chunks[pos].chunk_id for pos in bm25_order]
        vector_ids = [self.index.chunks[pos].chunk_id for pos in vector_order]
        fused = reciprocal_rank_fusion(bm25_ids, vector_ids, k=self.rrf_k)[
            : self.candidate_limit
        ]

        reranker_scores: dict[str, float] = {}
        if self.reranker is not None and fused:
            passages = [self.index.chunks[self.positions[row[0]]].content for row in fused]
            values = await self.reranker.score(query, passages)
            reranker_scores = {
                row[0]: score for row, score in zip(fused, values, strict=True)
            }
            fused = tuple(
                sorted(
                    fused,
                    key=lambda row: (-reranker_scores[row[0]], -row[1], row[0]),
                )
            )

        fused_rank_by_id = {
            row[0]: rank
            for rank, row in enumerate(
                reciprocal_rank_fusion(bm25_ids, vector_ids, k=self.rrf_k), 1
            )
        }
        hits: list[HybridSearchHit] = []
        for final_rank, (chunk_id, fused_score, bm25_rank, vector_rank) in enumerate(
            fused[:top_k], 1
        ):
            position = self.positions[chunk_id]
            chunk = self.index.chunks[position]
            # Result-level recheck protects against future mutable policy adapters.
            if not can_read_chunk(
                subject,
                tenant_id=chunk.tenant_id,
                department=chunk.department,
                classification=chunk.classification,
                allowed_access=chunk.allowed_access,
            ):
                continue
            hits.append(
                HybridSearchHit(
                    chunk=chunk,
                    final_rank=final_rank,
                    scores=RetrievalScoreBreakdown(
                        bm25_rank=bm25_rank,
                        vector_rank=vector_rank,
                        fused_rank=fused_rank_by_id[chunk_id],
                        reranker_score=reranker_scores.get(chunk_id),
                        bm25_score=(bm25_scores[position] if bm25_rank is not None else None),
                        vector_similarity=(
                            float(vector_scores[position]) if vector_rank is not None else None
                        ),
                        fused_score=fused_score,
                    ),
                )
            )
        return tuple(hits)
