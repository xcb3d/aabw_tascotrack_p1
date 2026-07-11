from __future__ import annotations

import hashlib
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.config import Settings, get_settings
from apps.api.src.db.models import Document, DocumentVersion, Job
from apps.api.src.dependencies import get_current_subject, get_db, get_request_id, require_idempotency_key
from apps.api.src.schemas.common import Classification
from apps.api.src.schemas.envelope import GenericEnvelope
from modules.identity.src.subject import SubjectContext
from modules.policy.src.engine import PolicyEngine
from modules.knowledge.src.storage import get_object_store

router = APIRouter(tags=["Documents"])


async def _authorized_document(db: AsyncSession, document_id: str, subject: SubjectContext, action: str) -> Document:
    try:
        key = uuid.UUID(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc
    row = await db.get(Document, key)
    if row is None or row.tenant_id != subject.tenant_id:
        raise HTTPException(status_code=404, detail="Document not found")
    decision = await PolicyEngine().decide(subject, {"tenant_id": row.tenant_id, "department_id": row.department_id, "classification": row.classification, "allowed_access": row.allowed_access, "status": row.status}, action)
    if decision.decision.value != "ALLOW":
        raise HTTPException(status_code=403, detail="Document operation denied")
    return row


@router.get("/mytasco/v1/aiwsp/documents", operation_id="listDocuments", response_model=GenericEnvelope)
async def list_documents(page: int = Query(0, ge=0), pageSize: int = Query(20, ge=1, le=100), request_id: str = Depends(get_request_id), subject: SubjectContext = Depends(get_current_subject), db: AsyncSession = Depends(get_db)) -> GenericEnvelope:
    rows = (await db.execute(select(Document).where(Document.tenant_id == subject.tenant_id).order_by(Document.created_at.desc()).offset(page * pageSize).limit(pageSize * 3))).scalars().all()
    visible = []
    for row in rows:
        decision = await PolicyEngine().decide(subject, {"tenant_id": row.tenant_id, "department_id": row.department_id, "classification": row.classification, "allowed_access": row.allowed_access, "status": row.status}, "document:list")
        if decision.decision.value == "ALLOW":
            visible.append({"documentId": str(row.id), "stableId": row.stable_id, "title": row.title, "departmentId": row.department_id, "classification": row.classification, "status": row.status, "currentVersionId": str(row.current_version_id) if row.current_version_id else None})
        if len(visible) >= pageSize:
            break
    return GenericEnvelope(body={"result": visible, "pageInfo": {"currentPage": page, "pageSize": pageSize, "hasNextPage": len(rows) > len(visible)}}, requestId=request_id)


async def _read_upload(file: UploadFile, settings: Settings) -> bytes:
    if file.content_type not in {"text/plain", "text/markdown", "application/octet-stream"} and not (file.filename or "").lower().endswith((".txt", ".md")):
        raise HTTPException(status_code=400, detail="Only UTF-8 text and Markdown are supported")
    data = await file.read(settings.MAX_UPLOAD_BYTES + 1)
    if not data or len(data) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Upload is empty or exceeds size limit")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Upload must be UTF-8") from exc
    return data


@router.post("/mytasco/v1/aiwsp/documents", operation_id="createDocument", response_model=GenericEnvelope, status_code=202)
async def create_document(file: UploadFile = File(...), title: str = Form(...), departmentId: str = Form(...), classification: str = Form(...), allowedAccess: list[str] | None = Form(None), idempotency_key: str = Depends(require_idempotency_key), request_id: str = Depends(get_request_id), subject: SubjectContext = Depends(get_current_subject), db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)) -> GenericEnvelope:
    del idempotency_key
    try:
        classification_value = Classification(classification).value
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid classification") from exc
    decision = await PolicyEngine().decide(subject, {"tenant_id": subject.tenant_id, "department_id": departmentId, "classification": classification_value}, "admin:document:create")
    if decision.decision.value != "ALLOW":
        raise HTTPException(status_code=403, detail="Document creation denied")
    data = await _read_upload(file, settings)
    row = Document(tenant_id=subject.tenant_id, stable_id=f"DOC-{uuid.uuid4().hex[:12].upper()}", title=title, department_id=departmentId, classification=classification_value, allowed_access=allowedAccess or ["All"], owner_id=subject.subject_id, status="draft")
    db.add(row)
    await db.flush()
    content_hash = hashlib.sha256(data).hexdigest()
    source_uri = await get_object_store(settings).put(f"{subject.tenant_id}/{row.id}/{content_hash}/{file.filename or 'document.md'}", data, file.content_type or "application/octet-stream")
    version = DocumentVersion(document_id=row.id, version_number=1, source_uri=source_uri, content_hash=content_hash, status="processing", raw_content=None)
    db.add(version)
    await db.flush()
    db.add(Job(queue="ingestion", job_type="ingest_document", payload={"documentId": str(row.id), "versionId": str(version.id)}))
    await db.commit()
    return GenericEnvelope(body={"documentId": str(row.id), "versionId": str(version.id), "status": "processing"}, requestId=request_id)


@router.post("/mytasco/v1/aiwsp/documents/{documentId}/versions", operation_id="createDocumentVersion", response_model=GenericEnvelope, status_code=202)
async def create_document_version(documentId: str, file: UploadFile = File(...), effectiveFrom: str | None = Form(None), idempotency_key: str = Depends(require_idempotency_key), request_id: str = Depends(get_request_id), subject: SubjectContext = Depends(get_current_subject), db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)) -> GenericEnvelope:
    del idempotency_key
    row = await _authorized_document(db, documentId, subject, "admin:document:version")
    data = await _read_upload(file, settings)
    count = int((await db.execute(select(func.count()).select_from(DocumentVersion).where(DocumentVersion.document_id == row.id))).scalar_one())
    try:
        effective = datetime.fromisoformat(effectiveFrom.replace("Z", "+00:00")) if effectiveFrom else None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid effectiveFrom") from exc
    content_hash = hashlib.sha256(data).hexdigest()
    source_uri = await get_object_store(settings).put(f"{subject.tenant_id}/{row.id}/{content_hash}/{file.filename or 'document.md'}", data, file.content_type or "application/octet-stream")
    version = DocumentVersion(document_id=row.id, version_number=count + 1, source_uri=source_uri, content_hash=content_hash, effective_from=effective, supersedes_id=row.current_version_id, status="processing", raw_content=None)
    db.add(version)
    await db.flush()
    db.add(Job(queue="ingestion", job_type="ingest_document", payload={"documentId": str(row.id), "versionId": str(version.id)}))
    await db.commit()
    return GenericEnvelope(body={"documentId": str(row.id), "versionId": str(version.id), "status": "processing"}, requestId=request_id)


@router.post("/mytasco/v1/aiwsp/documents/{documentId}/publish", operation_id="publishDocument", response_model=GenericEnvelope)
async def publish_document(documentId: str, idempotency_key: str = Depends(require_idempotency_key), request_id: str = Depends(get_request_id), subject: SubjectContext = Depends(get_current_subject), db: AsyncSession = Depends(get_db)) -> GenericEnvelope:
    del idempotency_key
    row = await _authorized_document(db, documentId, subject, "admin:document:publish")
    version = (await db.execute(select(DocumentVersion).where(DocumentVersion.document_id == row.id, DocumentVersion.status == "ready").order_by(DocumentVersion.version_number.desc()).with_for_update())).scalars().first()
    if version is None:
        raise HTTPException(status_code=409, detail="No ingested version is ready")
    if row.current_version_id:
        previous = await db.get(DocumentVersion, row.current_version_id)
        if previous:
            previous.status = "archived"
            previous.effective_to = datetime.now(previous.effective_from.tzinfo) if previous.effective_from else datetime.utcnow()
    version.status = "active"
    version.qa_metrics = {**version.qa_metrics, "published": True}
    row.current_version_id, row.status = version.id, "active"
    await db.commit()
    return GenericEnvelope(body={"documentId": str(row.id), "versionId": str(version.id), "status": "active"}, requestId=request_id)


@router.post("/mytasco/v1/aiwsp/documents/{documentId}/archive", operation_id="archiveDocument", response_model=GenericEnvelope)
async def archive_document(documentId: str, idempotency_key: str = Depends(require_idempotency_key), request_id: str = Depends(get_request_id), subject: SubjectContext = Depends(get_current_subject), db: AsyncSession = Depends(get_db)) -> GenericEnvelope:
    del idempotency_key
    row = await _authorized_document(db, documentId, subject, "admin:document:archive")
    row.status = "archived"
    if row.current_version_id:
        version = await db.get(DocumentVersion, row.current_version_id)
        if version:
            version.status = "archived"
            version.effective_to = datetime.now().astimezone()
    await db.commit()
    return GenericEnvelope(body={"documentId": str(row.id), "status": "archived"}, requestId=request_id)
