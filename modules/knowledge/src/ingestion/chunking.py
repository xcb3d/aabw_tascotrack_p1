"""Deterministic Markdown-aware chunking for Vietnamese enterprise documents."""

from __future__ import annotations

import hashlib
import re

from modules.knowledge.src.ingestion.models import ChunkRecord, DocumentRecord

HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$")


def _blocks(content: str) -> list[tuple[tuple[str, ...], str]]:
    heading_stack: list[str] = []
    current_path: tuple[str, ...] = ()
    current_lines: list[str] = []
    result: list[tuple[tuple[str, ...], str]] = []

    def flush() -> None:
        text = "\n".join(current_lines).strip()
        if text:
            result.append((current_path, text))

    for line in content.splitlines():
        match = HEADING_RE.match(line)
        if not match:
            current_lines.append(line)
            continue
        flush()
        current_lines = [line]
        level = len(match.group(1))
        heading_stack[level - 1 :] = [match.group(2).strip()]
        current_path = tuple(heading_stack)
    flush()
    return result


def _split_large_block(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    pieces: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", paragraph) if s.strip()]
        else:
            sentences = [paragraph]
        for sentence in sentences:
            candidate = f"{current}\n\n{sentence}".strip()
            if current and len(candidate) > max_chars:
                pieces.append(current)
                current = sentence
            else:
                current = candidate
    if current:
        pieces.append(current)
    return pieces


def chunk_document(document: DocumentRecord, *, max_chars: int = 1_600) -> tuple[ChunkRecord, ...]:
    """Split at Markdown section boundaries, retaining version and ACL metadata."""

    if max_chars < 200:
        raise ValueError("max_chars must be at least 200")
    chunks: list[ChunkRecord] = []
    for heading_path, block in _blocks(document.content_vi):
        for piece in _split_large_block(block, max_chars):
            ordinal = len(chunks)
            identity = f"{document.version_id}:{ordinal}:{piece}".encode("utf-8")
            chunk_id = f"CHK-{hashlib.sha256(identity).hexdigest()[:24]}"
            chunks.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    document_id=document.document_id,
                    version_id=document.version_id,
                    ordinal=ordinal,
                    heading_path=heading_path,
                    content=piece,
                    department=document.department,
                    classification=document.classification,
                    allowed_access=document.allowed_access,
                    language=document.language,
                )
            )
    return tuple(chunks)
