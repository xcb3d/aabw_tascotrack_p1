from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.db.models import AgentRun, AuditEvent, Document, RunEvent, SecurityEvent
from apps.api.src.dependencies import get_current_subject, get_db, get_request_id
from apps.api.src.schemas.envelope import GenericEnvelope
from modules.identity.src.subject import SubjectContext
from modules.policy.src.engine import PolicyEngine

router = APIRouter(tags=["Governance"])


def _admin(subject: SubjectContext) -> None:
    if not subject.is_admin:
        raise HTTPException(status_code=403, detail="Administrator role required")


@router.get("/mytasco/v1/aiwsp/permissions/explain", operation_id="explainPermission")
async def explain_permission(document_id: str = Query(..., alias="documentId"), request_id: str = Depends(get_request_id), subject: SubjectContext = Depends(get_current_subject), db: AsyncSession = Depends(get_db)) -> GenericEnvelope:
    clauses = [Document.tenant_id == subject.tenant_id, Document.stable_id == document_id]
    try:
        clauses = [Document.tenant_id == subject.tenant_id, or_(Document.stable_id == document_id, Document.id == uuid.UUID(document_id))]
    except ValueError:
        pass
    row = (await db.execute(select(Document).where(*clauses))).scalar_one_or_none()
    if row is None:
        return GenericEnvelope(body={"decision": "DENY", "reason": "RESOURCE_NOT_VISIBLE"}, requestId=request_id)
    decision = await PolicyEngine().decide(subject, {"tenant_id": row.tenant_id, "department_id": row.department_id, "classification": row.classification, "allowed_access": row.allowed_access, "status": row.status}, "knowledge:read", "KNOWLEDGE_SEARCH")
    return GenericEnvelope(body={"decision": decision.decision.value, "reason": decision.reason, "policyVersion": decision.policy_version, "decisionId": decision.decision_id}, requestId=request_id)


@router.get("/mytasco/v1/aiwsp/audit/recent", operation_id="getRecentAudit")
async def get_recent_audit(request_id: str = Depends(get_request_id), subject: SubjectContext = Depends(get_current_subject), db: AsyncSession = Depends(get_db)) -> GenericEnvelope:
    _admin(subject)
    rows = (await db.execute(select(AuditEvent).where(AuditEvent.tenant_id == subject.tenant_id).order_by(AuditEvent.created_at.desc()).limit(100))).scalars().all()
    return GenericEnvelope(body={"result": [{"eventId": str(row.id), "eventType": row.event_type, "actorId": row.actor_id, "requestId": row.request_id, "traceId": row.trace_id, "policyDecisionId": row.policy_decision_id, "metadata": row.payload, "createdAt": row.created_at.isoformat()} for row in rows]}, requestId=request_id)


@router.get("/mytasco/v1/aiwsp/admin/traces/{trace_id}", operation_id="getTrace")
async def get_trace(trace_id: str, request_id: str = Depends(get_request_id), subject: SubjectContext = Depends(get_current_subject), db: AsyncSession = Depends(get_db)) -> GenericEnvelope:
    _admin(subject)
    try:
        trace_uuid = uuid.UUID(trace_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Trace not found") from exc
    run = (await db.execute(select(AgentRun).where(AgentRun.trace_id == trace_uuid, AgentRun.tenant_id == subject.tenant_id))).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    events = (await db.execute(select(RunEvent).where(RunEvent.run_id == run.id).order_by(RunEvent.id))).scalars().all()
    return GenericEnvelope(body={"traceId": trace_id, "runId": str(run.id), "route": run.route, "status": run.status, "events": [{"status": event.status, "metadata": event.payload, "createdAt": event.created_at.isoformat()} for event in events]}, requestId=request_id)


@router.get("/mytasco/v1/aiwsp/admin/security-events", operation_id="listSecurityEvents")
async def list_security_events(request_id: str = Depends(get_request_id), subject: SubjectContext = Depends(get_current_subject), db: AsyncSession = Depends(get_db)) -> GenericEnvelope:
    _admin(subject)
    rows = (await db.execute(select(SecurityEvent).where(SecurityEvent.tenant_id == subject.tenant_id).order_by(SecurityEvent.created_at.desc()).limit(100))).scalars().all()
    return GenericEnvelope(body={"result": [{"eventId": str(row.id), "eventType": row.event_type, "severity": row.severity, "traceId": row.trace_id, "metadata": row.details, "createdAt": row.created_at.isoformat()} for row in rows]}, requestId=request_id)
