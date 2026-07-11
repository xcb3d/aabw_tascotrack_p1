"""Canonical, storage-independent models for the AIE1 ingestion boundary."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

Classification = Literal["Public", "Internal", "Confidential", "Restricted"]
AllowedAccess = Literal["All", "All Employees", "Own Department", "Executive Only"]


@dataclass(frozen=True)
class DocumentRecord:
    document_id: str
    version_id: str
    title: str
    department: str
    classification: Classification
    content_vi: str
    owner: str
    allowed_access: AllowedAccess
    last_updated: str
    tags: tuple[str, ...]
    language: str
    declared_word_count: int
    source_sheet: str
    source_row: int
    source_sha256: str

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["tags"] = list(self.tags)
        return value


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    document_id: str
    version_id: str
    ordinal: int
    heading_path: tuple[str, ...]
    content: str
    department: str
    classification: Classification
    allowed_access: AllowedAccess
    language: str

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["heading_path"] = list(self.heading_path)
        return value


@dataclass(frozen=True)
class QuarantineRecord:
    source_sheet: str
    source_row: int
    document_id: str | None
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["reasons"] = list(self.reasons)
        return value


@dataclass(frozen=True)
class CorpusLoadResult:
    documents: tuple[DocumentRecord, ...]
    quarantined: tuple[QuarantineRecord, ...]
