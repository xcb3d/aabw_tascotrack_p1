from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.config import Settings
from apps.api.src.db.models import Chunk, Document, DocumentVersion, SecurityEvent
from modules.guardrails.src.dlp.screening import sensitivity_gate
from modules.guardrails.src.dlp import scan_input
from modules.knowledge.src.embeddings import TextToEmbed, load_embedding_config
from modules.knowledge.src.embeddings.qwen3 import Qwen3Embedder
from modules.knowledge.src.ingestion.chunking import chunk_document
from modules.knowledge.src.ingestion.models import DocumentRecord
from modules.knowledge.src.ingestion.models import AllowedAccess, Classification as IngestionClassification
from modules.knowledge.src.storage import get_object_store


def _access(value: list) -> str:
    known = {"All", "All Employees", "Own Department", "Executive Only"}
    return next((item for item in value if item in known), "Own Department")


async def ingest_document_job(session: AsyncSession, document_id: str, version_id: str, settings: Settings) -> None:
    document = await session.get(Document, uuid.UUID(document_id))
    version = await session.get(DocumentVersion, uuid.UUID(version_id))
    if document is None or version is None or version.document_id != document.id:
        raise LookupError("document version not found")
    if version.status in {"ready", "active"}:
        return
    try:
        source = version.raw_content if version.raw_content is not None else await get_object_store(settings).get(version.source_uri or "")
        content = source.decode("utf-8")
    except UnicodeDecodeError:
        version.status, version.quarantine_reasons = "quarantined", ["INVALID_UTF8"]
        version.steward_review_required = True
        version.qa_metrics = {"published": False, "reason": "INVALID_UTF8"}
        await session.commit()
        return
    codes = sensitivity_gate(content).codes
    blocked_codes = {"PRIVATE_KEY", "BEARER_TOKEN", "AUTH_TOKEN", "OTP", "COOKIE", "PAYROLL"}
    if blocked_codes.intersection(codes):
        version.status, version.quarantine_reasons = "quarantined", sorted(blocked_codes.intersection(codes))
        version.steward_review_required = True
        version.qa_metrics = {"published": False, "dlpCodes": version.quarantine_reasons}
        session.add(SecurityEvent(tenant_id=document.tenant_id, event_type="INGESTION_DLP_BLOCK", severity="HIGH", actor_id=document.owner_id, details={"documentId": str(document.id), "codes": version.quarantine_reasons}))
        await session.commit()
        return
    record = DocumentRecord(
        document_id=str(document.id), version_id=str(version.id), title=document.title,
        department=document.department_id, classification=cast(IngestionClassification, document.classification),
        content_vi=content, owner=document.owner_id, allowed_access=cast(AllowedAccess, _access(document.allowed_access)),
        last_updated=datetime.now(timezone.utc).date().isoformat(), tags=(), language="vi",
        declared_word_count=len(content.split()), source_sheet="upload", source_row=0,
        source_sha256=version.content_hash,
    )
    chunks = chunk_document(record)
    await session.execute(delete(Chunk).where(Chunk.version_id == version.id))
    embeddings: dict[str, tuple[float, ...]] = {}
    if settings.INTERNAL_EMBEDDINGS_ENABLED and document.classification != "Restricted":
        embedder = Qwen3Embedder(load_embedding_config(Path("config/models/embedding-qwen3-0.6b.json")))
        inputs = [TextToEmbed(chunk_id=item.chunk_id, tenant_id=document.tenant_id, document_version_id=str(version.id), classification=document.classification, content=item.content, content_sha256=hashlib.sha256(item.content.encode()).hexdigest()) for item in chunks]
        results = await embedder.embed_documents(inputs)
        embeddings = {item.chunk_id: item.values for item in results}
    for item in chunks:
        annotations = scan_input(item.content)
        session.add(Chunk(
            tenant_id=document.tenant_id, stable_id=item.chunk_id, document_id=document.id,
            version_id=version.id, ordinal=item.ordinal, heading_path=list(item.heading_path),
            section=" > ".join(item.heading_path), content=item.content,
            content_hash=hashlib.sha256(item.content.encode()).hexdigest(),
            department_id=document.department_id, classification=document.classification,
            allowed_access=document.allowed_access, annotations={"dlpCodes": annotations["codes"], "piiTypes": annotations["piiTypes"], "promptInjection": "PROMPT_INJECTION" in annotations["codes"]},
            embedding=embeddings.get(item.chunk_id),
        ))
    version.status = "ready"
    version.steward_review_required = False
    version.qa_metrics = {"published": False, "chunkCount": len(chunks), "wordCount": len(content.split()), "contentHashVerified": hashlib.sha256(source).hexdigest() == version.content_hash, "embeddingCount": len(embeddings), "piiAnnotatedChunks": sum(bool(scan_input(item.content)["piiTypes"]) for item in chunks), "promptInjectionChunks": sum("PROMPT_INJECTION" in scan_input(item.content)["codes"] for item in chunks)}
    await session.commit()
