import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, HTTPException
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.dependencies import get_request_id, require_idempotency_key, get_current_subject, get_db
from apps.api.src.db.models import Document
from apps.api.src.schemas.envelope import GenericEnvelope
from apps.api.src.schemas.common import ErrorCode
from modules.identity.src.subject import SubjectContext

router = APIRouter(tags=["Documents"])


@router.get(
    "/mytasco/v1/aiwsp/documents",
    operation_id="listDocuments",
    response_model=GenericEnvelope,
)
async def list_documents(
    page: int = Query(default=0, ge=0),
    pageSize: int = Query(default=20, ge=1, le=100),
    subject: SubjectContext = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> GenericEnvelope:
    """listDocuments — GET /mytasco/v1/aiwsp/documents

    List documents visible to the caller.
    """
    is_executive = 'Executive' in subject.roles
    user_dept = subject.departments[0] if subject.departments else 'unknown'

    stmt = select(Document)
    if not is_executive:
        stmt = stmt.where(
            or_(
                Document.allowed_access == 'All',
                Document.allowed_access == 'All Employees',
                and_(
                    Document.allowed_access == 'Own Department',
                    Document.department_id == user_dept
                )
            )
        )
    stmt = stmt.offset(page * pageSize).limit(pageSize)
    result = await db.execute(stmt)
    docs = result.scalars().all()

    formatted_docs = []
    for doc in docs:
        formatted_docs.append({
            "id": str(doc.id),
            "documentId": doc.document_id,
            "title": doc.title,
            "departmentId": doc.department_id,
            "classification": doc.classification,
            "owner": doc.owner,
            "allowedAccess": doc.allowed_access,
            "lastUpdated": doc.last_updated.isoformat(),
            "wordCount": doc.word_count,
            "status": doc.status
        })

    return GenericEnvelope(
        status="success",
        message="SUCCESS",
        requestId=request_id,
        body=formatted_docs
    )


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
    subject: SubjectContext = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> GenericEnvelope:
    """createDocument — POST /mytasco/v1/aiwsp/documents

    Create document metadata and an ingestion job.
    """
    doc_uuid = uuid.uuid4()
    doc_id = f"DOC{uuid.uuid4().hex[:3].upper()}"
    
    # allowed_access computed column will handle it in DB, but we pass classification
    new_doc = Document(
        id=doc_uuid,
        document_id=doc_id,
        title=title,
        department_id=departmentId,
        classification=classification,
        owner=subject.subject_id,
        last_updated=datetime.now(timezone.utc),
        tags=[],
        language="vi",
        word_count=0,
        content="",
        status="Ingesting"
    )
    db.add(new_doc)
    await db.commit()

    return GenericEnvelope(
        status="success",
        message="SUCCESS",
        requestId=request_id,
        body={
            "id": str(doc_uuid),
            "documentId": doc_id,
            "title": title,
            "status": "Ingesting"
        }
    )


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
    subject: SubjectContext = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> GenericEnvelope:
    """createDocumentVersion — POST /mytasco/v1/aiwsp/documents/{documentId}/versions

    Upload a new immutable document version.
    """
    # Find document
    stmt = select(Document).where(Document.document_id == documentId)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "code": ErrorCode.NOT_FOUND.value,
                "message": f"Document '{documentId}' not found",
                "requestId": request_id,
            }
        )

    doc.last_updated = datetime.now(timezone.utc)
    doc.status = "Ingesting"
    await db.commit()

    return GenericEnvelope(
        status="success",
        message="SUCCESS",
        requestId=request_id,
        body={
            "documentId": documentId,
            "status": "Ingesting",
            "message": "New version upload received"
        }
    )


@router.post(
    "/mytasco/v1/aiwsp/documents/{documentId}/publish",
    operation_id="publishDocument",
    response_model=GenericEnvelope,
)
async def publish_document(
    documentId: str,
    idempotency_key: str = Depends(require_idempotency_key),
    subject: SubjectContext = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> GenericEnvelope:
    """publishDocument — POST /mytasco/v1/aiwsp/documents/{documentId}/publish

    Publish an ingested and classified document version.
    """
    stmt = select(Document).where(Document.document_id == documentId)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "code": ErrorCode.NOT_FOUND.value,
                "message": f"Document '{documentId}' not found",
                "requestId": request_id,
            }
        )

    doc.status = "Active"
    await db.commit()

    return GenericEnvelope(
        status="success",
        message="SUCCESS",
        requestId=request_id,
        body={
            "documentId": documentId,
            "status": "Active",
            "message": "Document published successfully"
        }
    )


@router.post(
    "/mytasco/v1/aiwsp/documents/{documentId}/archive",
    operation_id="archiveDocument",
    response_model=GenericEnvelope,
)
async def archive_document(
    documentId: str,
    idempotency_key: str = Depends(require_idempotency_key),
    subject: SubjectContext = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> GenericEnvelope:
    """archiveDocument — POST /mytasco/v1/aiwsp/documents/{documentId}/archive

    Archive an active document version.
    """
    stmt = select(Document).where(Document.document_id == documentId)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "code": ErrorCode.NOT_FOUND.value,
                "message": f"Document '{documentId}' not found",
                "requestId": request_id,
            }
        )

    doc.status = "Archived"
    await db.commit()

    return GenericEnvelope(
        status="success",
        message="SUCCESS",
        requestId=request_id,
        body={
            "documentId": documentId,
            "status": "Archived",
            "message": "Document archived successfully"
        }
    )


@router.get(
    "/mytasco/v1/aiwsp/documents/{documentId}",
    operation_id="getDocument",
    response_model=GenericEnvelope,
)
async def get_document(
    documentId: str,
    subject: SubjectContext = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> GenericEnvelope:
    """getDocument — GET /mytasco/v1/aiwsp/documents/{documentId}

    Get details of a specific document, including content, if authorized.
    """
    stmt = select(Document).where(Document.document_id == documentId)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "code": ErrorCode.NOT_FOUND.value,
                "message": f"Document '{documentId}' not found",
                "requestId": request_id,
            }
        )

    # ACL Check
    is_executive = 'Executive' in subject.roles
    user_dept = subject.departments[0] if subject.departments else 'unknown'
    
    allowed = False
    if is_executive:
        allowed = True
    elif doc.allowed_access == 'All' or doc.allowed_access == 'All Employees':
        allowed = True
    elif doc.allowed_access == 'Own Department' and doc.department_id == user_dept:
        allowed = True

    if not allowed:
        raise HTTPException(
            status_code=403,
            detail={
                "status": "error",
                "code": ErrorCode.FORBIDDEN.value,
                "message": f"Access denied to document '{documentId}'",
                "requestId": request_id,
            }
        )

    return GenericEnvelope(
        status="success",
        message="SUCCESS",
        requestId=request_id,
        body={
            "id": str(doc.id),
            "documentId": doc.document_id,
            "title": doc.title,
            "departmentId": doc.department_id,
            "classification": doc.classification,
            "owner": doc.owner,
            "allowedAccess": doc.allowed_access,
            "lastUpdated": doc.last_updated.isoformat(),
            "wordCount": doc.word_count,
            "status": doc.status,
            "content": doc.content
        }
    )

