from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from apps.api.src.dependencies import get_request_id, require_idempotency_key
from apps.api.src.schemas.envelope import GenericEnvelope

router = APIRouter(tags=["Documents"])


@router.get(
    "/mytasco/v1/aiwsp/documents",
    operation_id="listDocuments",
    response_model=GenericEnvelope,
)
async def list_documents(
    page: int = Query(default=0, ge=0),
    pageSize: int = Query(default=20, ge=1, le=100),
    request_id: str = Depends(get_request_id),
) -> GenericEnvelope:
    """listDocuments — GET /mytasco/v1/aiwsp/documents

    List documents visible to the caller.
    """
    # TODO: paginated document listing with ACL filtering.
    raise NotImplementedError("listDocuments")


@router.post(
    "/mytasco/v1/aiwsp/documents",
    operation_id="createDocument",
    response_model=GenericEnvelope,
    status_code=202,
)
async def create_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    departmentId: str = Form(...),
    classification: str = Form(...),
    allowedAccess: list[str] | None = Form(default=None),
    idempotency_key: str = Depends(require_idempotency_key),
    request_id: str = Depends(get_request_id),
) -> GenericEnvelope:
    """createDocument — POST /mytasco/v1/aiwsp/documents

    Create document metadata and an ingestion job.
    """
    # TODO: validate form, persist metadata, enqueue ingestion worker job.
    raise NotImplementedError("createDocument")


@router.post(
    "/mytasco/v1/aiwsp/documents/{documentId}/versions",
    operation_id="createDocumentVersion",
    response_model=GenericEnvelope,
    status_code=202,
)
async def create_document_version(
    documentId: str,
    file: UploadFile = File(...),
    effectiveFrom: str | None = Form(default=None),
    idempotency_key: str = Depends(require_idempotency_key),
    request_id: str = Depends(get_request_id),
) -> GenericEnvelope:
    """createDocumentVersion — POST /mytasco/v1/aiwsp/documents/{documentId}/versions

    Upload a new immutable document version.
    """
    # TODO: persist version, enqueue re-ingestion.
    raise NotImplementedError("createDocumentVersion")


@router.post(
    "/mytasco/v1/aiwsp/documents/{documentId}/publish",
    operation_id="publishDocument",
    response_model=GenericEnvelope,
)
async def publish_document(
    documentId: str,
    idempotency_key: str = Depends(require_idempotency_key),
    request_id: str = Depends(get_request_id),
) -> GenericEnvelope:
    """publishDocument — POST /mytasco/v1/aiwsp/documents/{documentId}/publish

    Publish an ingested and classified document version.
    """
    # TODO: transition document status to published; update index.
    raise NotImplementedError("publishDocument")


@router.post(
    "/mytasco/v1/aiwsp/documents/{documentId}/archive",
    operation_id="archiveDocument",
    response_model=GenericEnvelope,
)
async def archive_document(
    documentId: str,
    idempotency_key: str = Depends(require_idempotency_key),
    request_id: str = Depends(get_request_id),
) -> GenericEnvelope:
    """archiveDocument — POST /mytasco/v1/aiwsp/documents/{documentId}/archive

    Archive an active document version.
    """
    # TODO: transition document status to archived.
    raise NotImplementedError("archiveDocument")
