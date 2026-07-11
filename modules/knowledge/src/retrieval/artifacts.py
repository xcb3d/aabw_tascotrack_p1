"""Read the AIE1 JSONL handoff as an AIE2 development index."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class ArtifactChunk:
    chunk_id: str
    tenant_id: str
    document_id: str
    document_version_id: str
    title: str
    heading_path: tuple[str, ...]
    content: str
    department: str
    classification: str
    allowed_access: str

    @property
    def bm25_text(self) -> str:
        headings = " ".join(self.heading_path)
        return f"{self.title} {self.title} {headings} {self.content}"


@dataclass(frozen=True)
class ArtifactIndex:
    chunks: tuple[ArtifactChunk, ...]
    vectors: np.ndarray
    model_id: str
    model_revision: str
    dimension: int


def _jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_artifact_index(
    *, chunks_path: Path, documents_path: Path, embeddings_path: Path
) -> ArtifactIndex:
    documents = {row["document_id"]: row for row in _jsonl(documents_path)}
    embedding_rows = _jsonl(embeddings_path)
    embeddings = {row["chunk_id"]: row for row in embedding_rows}
    chunks: list[ArtifactChunk] = []
    vectors: list[list[float]] = []
    seen: set[str] = set()
    for row in _jsonl(chunks_path):
        chunk_id = row["chunk_id"]
        if chunk_id in seen:
            raise ValueError(f"duplicate chunk_id {chunk_id!r}")
        seen.add(chunk_id)
        embedding = embeddings.get(chunk_id)
        if embedding is None:
            raise ValueError(f"missing embedding for {chunk_id}")
        document = documents[row["document_id"]]
        chunks.append(
            ArtifactChunk(
                chunk_id=chunk_id,
                tenant_id=embedding["tenant_id"],
                document_id=row["document_id"],
                document_version_id=row["version_id"],
                title=document["title"],
                heading_path=tuple(row["heading_path"]),
                content=row["content"],
                department=row["department"],
                classification=row["classification"],
                allowed_access=row["allowed_access"],
            )
        )
        vectors.append(embedding["embedding"])
    if set(embeddings) != seen:
        raise ValueError("embedding artifact contains unknown chunk IDs")
    matrix = np.asarray(vectors, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[0] != len(chunks):
        raise ValueError("invalid embedding matrix")
    norms = np.linalg.norm(matrix, axis=1)
    if not np.all(np.isfinite(matrix)) or not np.allclose(norms, 1.0, atol=1e-4):
        raise ValueError("artifact vectors must be finite and normalized")
    first = embedding_rows[0]
    if matrix.shape[1] != first["dimension"]:
        raise ValueError("artifact dimension mismatch")
    return ArtifactIndex(
        chunks=tuple(chunks),
        vectors=matrix,
        model_id=first["model_id"],
        model_revision=first["model_revision"],
        dimension=first["dimension"],
    )
