from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from modules.knowledge.src.embeddings import EmbeddingRecord, load_embedding_config
from modules.knowledge.src.embeddings.config import EmbeddingModelConfig
from modules.knowledge.src.retrieval.contracts import RetrievalScoreBreakdown
from apps.worker.src.jobs.ingestion.embed_dataset import _read_chunks

CONFIG = Path("config/models/embedding-qwen3-0.6b.json")


def test_qwen3_registry_locks_internal_512_dimension_contract() -> None:
    config = load_embedding_config(CONFIG)

    assert config.model_id == "Qwen/Qwen3-Embedding-0.6B"
    assert config.execution == "internal_only"
    assert config.native_dimension == 1024
    assert config.output_dimension == 512
    assert config.normalize is True
    assert config.distance == "cosine"
    assert config.storage_type == "halfvec"
    assert config.classification_policy["Secret"] == "block"
    assert config.revision == "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
    assert config.is_production_pinned


def test_embedding_registry_rejects_secret_embedding() -> None:
    config = load_embedding_config(CONFIG)
    value = config.model_dump()
    value["classification_policy"]["Secret"] = "embed_internal"

    with pytest.raises(ValidationError, match="Secret content must never be embedded"):
        EmbeddingModelConfig.model_validate(value)


def test_embedding_record_rejects_wrong_vector_dimension() -> None:
    with pytest.raises(ValueError, match="value count"):
        EmbeddingRecord(
            chunk_id="CHK-1",
            tenant_id="TENANT-1",
            document_version_id="DOC-1-v1",
            model_id="Qwen/Qwen3-Embedding-0.6B",
            model_revision="revision",
            dimension=2,
            normalized=True,
            values=(0.1,),
            content_sha256="abc",
        )


def test_embedding_record_accepts_unit_normalized_vector() -> None:
    record = EmbeddingRecord(
        chunk_id="CHK-1",
        tenant_id="TENANT-1",
        document_version_id="DOC-1-v1",
        model_id="Qwen/Qwen3-Embedding-0.6B",
        model_revision="revision",
        dimension=2,
        normalized=True,
        values=(0.6, 0.8),
        content_sha256="abc",
    )
    assert record.dimension == 2


def test_retrieval_score_contract_uses_one_based_ranks() -> None:
    scores = RetrievalScoreBreakdown(
        bm25_rank=2,
        vector_rank=1,
        fused_rank=1,
        reranker_score=0.91,
    )
    assert scores.fused_rank == 1

    with pytest.raises(ValueError, match="one-based"):
        RetrievalScoreBreakdown(
            bm25_rank=0,
            vector_rank=None,
            fused_rank=1,
            reranker_score=None,
        )


def test_embedding_command_reads_prepared_chunks() -> None:
    items = _read_chunks(Path("database/seeds/aie1/chunks.jsonl"), "demo-mytasco")

    assert len(items) == 361
    assert items[0].tenant_id == "demo-mytasco"
    assert len(items[0].content_sha256) == 64
