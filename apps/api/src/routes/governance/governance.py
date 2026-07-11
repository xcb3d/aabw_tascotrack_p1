from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from apps.api.src.dependencies import get_request_id
from apps.api.src.schemas.envelope import GenericEnvelope

router = APIRouter(tags=["Governance"])


@router.get("/mytasco/v1/aiwsp/permissions/explain", operation_id="explainPermission")
async def explain_permission(
    document_id: str = Query(...),
    request_id: str = Depends(get_request_id),
) -> GenericEnvelope:
    """Explain an allow/deny decision without leaking denied metadata."""
    # TODO: evaluate policy engine and return safe explanation.
    raise NotImplementedError("explainPermission")


@router.get("/mytasco/v1/aiwsp/audit/recent", operation_id="getRecentAudit")
async def get_recent_audit(
    request_id: str = Depends(get_request_id),
) -> GenericEnvelope:
    """Get recent content-free audit events."""
    # TODO: query audit_events table ordered by created_at DESC.
    raise NotImplementedError("getRecentAudit")


@router.get("/mytasco/v1/aiwsp/admin/traces/{trace_id}", operation_id="getTrace")
async def get_trace(trace_id: str) -> GenericEnvelope:
    """Get authorized high-level trace without chain-of-thought."""
    # TODO: load trace metadata from traces table.
    raise NotImplementedError("getTrace")


@router.get("/mytasco/v1/aiwsp/admin/security-events", operation_id="listSecurityEvents")
async def list_security_events(
    request_id: str = Depends(get_request_id),
) -> GenericEnvelope:
    """List authorized security events."""
    # TODO: query security_events table.
    raise NotImplementedError("listSecurityEvents")