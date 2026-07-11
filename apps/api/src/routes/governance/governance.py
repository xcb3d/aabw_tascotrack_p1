import uuid
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.dependencies import get_request_id, get_current_subject, get_db
from apps.api.src.db.models import AuditEvent, Document
from apps.api.src.schemas.envelope import GenericEnvelope
from apps.api.src.schemas.common import ErrorCode, PermissionDecision
from modules.identity.src.subject import SubjectContext

router = APIRouter(tags=["Governance"])


@router.get("/mytasco/v1/aiwsp/permissions/explain", operation_id="explainPermission")
async def explain_permission(
    document_id: str = Query(...),
    subject: SubjectContext = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> GenericEnvelope:
    """Explain an allow/deny decision without leaking denied metadata."""
    stmt = select(Document).where(Document.document_id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "code": ErrorCode.NOT_FOUND.value,
                "message": f"Document '{document_id}' not found",
                "requestId": request_id,
            }
        )

    # Evaluate decision
    is_executive = 'Executive' in subject.roles
    user_dept = subject.departments[0] if subject.departments else 'unknown'
    decision = PermissionDecision.DENY

    if is_executive:
        decision = PermissionDecision.ALLOW
    else:
        if doc.allowed_access == 'All':
            decision = PermissionDecision.ALLOW
        elif doc.allowed_access == 'All Employees':
            decision = PermissionDecision.ALLOW
        elif doc.allowed_access == 'Own Department' and doc.department_id == user_dept:
            decision = PermissionDecision.ALLOW

    return GenericEnvelope(
        status="success",
        message="SUCCESS",
        requestId=request_id,
        body={
            "documentId": document_id,
            "decision": decision.value,
            "reason": "Evaluated against document classification and subject principal scopes."
        }
    )


@router.get("/mytasco/v1/aiwsp/audit/recent", operation_id="getRecentAudit")
async def get_recent_audit(
    subject: SubjectContext = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> GenericEnvelope:
    """Get recent content-free audit events."""
    # Restrict to Executive role
    if "Executive" not in subject.roles:
        raise HTTPException(
            status_code=403,
            detail={
                "status": "error",
                "code": ErrorCode.FORBIDDEN.value,
                "message": "Access denied. Only Executive role can view audit events.",
                "requestId": request_id,
            }
        )

    stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(50)
    result = await db.execute(stmt)
    events = result.scalars().all()

    formatted_events = []
    for ev in events:
        formatted_events.append({
            "id": str(ev.id),
            "sequenceNo": ev.sequence_no,
            "runId": str(ev.run_id) if ev.run_id else None,
            "eventType": ev.event_type,
            "actorUserId": str(ev.actor_user_id) if ev.actor_user_id else None,
            "requestId": ev.request_id,
            "payload": ev.payload,
            "createdAt": ev.created_at.isoformat()
        })

    return GenericEnvelope(
        status="success",
        message="SUCCESS",
        requestId=request_id,
        body=formatted_events
    )


@router.get("/mytasco/v1/aiwsp/admin/traces/{trace_id}", operation_id="getTrace")
async def get_trace(
    trace_id: str,
    subject: SubjectContext = Depends(get_current_subject),
    request_id: str = Depends(get_request_id),
) -> GenericEnvelope:
    """Get authorized high-level trace without chain-of-thought."""
    return GenericEnvelope(
        status="success",
        message="SUCCESS",
        requestId=request_id,
        body={
            "traceId": trace_id,
            "authorized": True,
            "message": "Trace retrieval mocked"
        }
    )


@router.get("/mytasco/v1/aiwsp/admin/security-events", operation_id="listSecurityEvents")
async def list_security_events(
    subject: SubjectContext = Depends(get_current_subject),
    request_id: str = Depends(get_request_id),
) -> GenericEnvelope:
    """List authorized security events."""
    return GenericEnvelope(
        status="success",
        message="SUCCESS",
        requestId=request_id,
        body=[]
    )