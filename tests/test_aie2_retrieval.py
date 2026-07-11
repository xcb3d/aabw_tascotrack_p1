from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from modules.knowledge.src.retrieval.artifacts import load_artifact_index
from modules.knowledge.src.retrieval.filters import RetrievalSubject, can_read_chunk
from modules.knowledge.src.retrieval.hybrid import HybridRetriever
from modules.knowledge.src.retrieval.rrf import reciprocal_rank_fusion


class FakeEmbedder:
    def __init__(self, vector: np.ndarray) -> None:
        self.vector = tuple(float(value) for value in vector)

    async def embed_query(self, query: str, *, tenant_id: str) -> tuple[float, ...]:
        del query, tenant_id
        return self.vector


@pytest.fixture(scope="module")
def artifact_index():
    return load_artifact_index(
        chunks_path=Path("database/seeds/aie1/chunks.jsonl"),
        documents_path=Path("database/seeds/aie1/documents.jsonl"),
        embeddings_path=Path("database/seeds/aie1/embeddings.jsonl"),
    )


def test_rrf_merges_by_stable_chunk_id() -> None:
    rows = reciprocal_rank_fusion(["a", "b"], ["b", "c"])

    assert rows[0][0] == "b"
    assert rows[0][2:] == (2, 1)
    assert {row[0] for row in rows} == {"a", "b", "c"}


def test_permission_matrix_normalizes_hr_department() -> None:
    subject = RetrievalSubject("demo-mytasco", "U001", "Human Resources", "Employee")

    assert can_read_chunk(
        subject,
        tenant_id="demo-mytasco",
        department="HR",
        classification="Confidential",
        allowed_access="Own Department",
    )
    assert not can_read_chunk(
        subject,
        tenant_id="demo-mytasco",
        department="Finance",
        classification="Confidential",
        allowed_access="Own Department",
    )


@pytest.mark.asyncio
async def test_cross_tenant_search_returns_no_candidates(artifact_index) -> None:
    retriever = HybridRetriever(artifact_index, FakeEmbedder(artifact_index.vectors[0]))
    subject = RetrievalSubject("other-tenant", "U001", "Human Resources", "Employee")

    assert await retriever.search("thử việc", subject) == ()


@pytest.mark.asyncio
async def test_restricted_document_is_visible_only_to_executive(artifact_index) -> None:
    target_position = next(
        position
        for position, chunk in enumerate(artifact_index.chunks)
        if chunk.document_id == "DOC040"
        and any("Roadmap" in heading for heading in chunk.heading_path)
    )
    retriever = HybridRetriever(
        artifact_index, FakeEmbedder(artifact_index.vectors[target_position])
    )
    employee = RetrievalSubject("demo-mytasco", "U001", "Human Resources", "Employee")
    executive = RetrievalSubject("demo-mytasco", "U031", "Executive Office", "Executive")

    employee_hits = await retriever.search("Lộ trình chuyển đổi số 2026", employee)
    executive_hits = await retriever.search("Lộ trình chuyển đổi số 2026", executive)

    assert all(hit.chunk.document_id != "DOC040" for hit in employee_hits)
    assert any(hit.chunk.document_id == "DOC040" for hit in executive_hits)
