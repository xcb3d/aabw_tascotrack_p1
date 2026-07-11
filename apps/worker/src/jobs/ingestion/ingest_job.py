from __future__ import annotations

from modules.guardrails.src.dlp import scan_input


async def ingest_document_job(document_id: str) -> None:
    """Ingest, classify, chunk, and index a document.

    # TODO: load source document, run DLP/sensitivity, persist immutable version and vectors.
    """
    scan_input(document_id)
    raise NotImplementedError("ingest_document_job")
