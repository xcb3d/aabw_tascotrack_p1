from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.config import Settings, get_settings
from apps.api.src.db.models import Action, AuditEvent
from apps.api.src.dependencies import get_current_subject, get_db, get_request_id, require_idempotency_key
from apps.api.src.schemas.action import ActionEnvelope, ActionPreview, ConfirmActionRequest
from apps.api.src.schemas.common import ActionStatus
from modules.identity.src.subject import SubjectContext
from modules.policy.src.engine import PolicyEngine
from modules.tools.src.actions import canonical_action_hash, token_hash, verify_confirmation_token
from modules.tools.src.mocks import default_mock_registry

router = APIRouter(tags=["Actions"])


def _preview(row: Action, request_id: str, *, include_token: bool = False) -> ActionEnvelope:
    return ActionEnvelope(body=ActionPreview(
        actionId=row.id, actionType=row.action_type, status=ActionStatus(row.status), summary=row.summary,
        parameters=row.parameters, impact=row.impact, expiresAt=row.expires_at,
        confirmationToken=row.result.get("confirmationToken") if include_token else None,
    ), requestId=request_id)


async def _owned(db: AsyncSession, action_id: str, subject: SubjectContext, *, lock: bool = False) -> Action:
    try:
        key = uuid.UUID(action_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Action not found") from exc
    query = select(Action).where(Action.id == key)
    if lock:
        query = query.with_for_update()
    row = (await db.execute(query)).scalar_one_or_none()
    if row is None or row.tenant_id != subject.tenant_id or row.owner_id != subject.subject_id:
        raise HTTPException(status_code=404, detail="Action not found")
    return row


@router.get("/mytasco/v1/aiwsp/actions/{action_id}", operation_id="getActionPreview")
async def get_action_preview(action_id: str, request_id: str = Depends(get_request_id), subject: SubjectContext = Depends(get_current_subject), db: AsyncSession = Depends(get_db)) -> ActionEnvelope:
    return _preview(await _owned(db, action_id, subject), request_id, include_token=True)


@router.post("/mytasco/v1/aiwsp/actions/{action_id}/confirm", operation_id="confirmAction")
async def confirm_action(
    action_id: str, body: ConfirmActionRequest,
    idempotency_key: str = Depends(require_idempotency_key), request_id: str = Depends(get_request_id),
    subject: SubjectContext = Depends(get_current_subject), db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ActionEnvelope:
    del idempotency_key
    if not settings.MOCK_ADAPTERS_ENABLED:
        raise HTTPException(status_code=503, detail="My Tasco business adapters are not configured")
    row = await _owned(db, action_id, subject, lock=True)
    if row.status == ActionStatus.COMPLETED.value:
        return _preview(row, request_id)
    if row.status != ActionStatus.WAITING_CONFIRMATION.value:
        raise HTTPException(status_code=409, detail="Action is not awaiting confirmation")
    if row.expires_at <= datetime.now(timezone.utc):
        row.status = ActionStatus.EXPIRED.value
        await db.commit()
        raise HTTPException(status_code=410, detail="Confirmation expired")
    claims = verify_confirmation_token(body.confirmationToken, settings.CONFIRMATION_SIGNING_KEY)
    if claims.get("action_id") != str(row.id) or claims.get("owner_id") != subject.subject_id or claims.get("tenant_id") != subject.tenant_id:
        raise HTTPException(status_code=403, detail="Confirmation scope mismatch")
    if not __import__("hmac").compare_digest(row.confirmation_token_hash, token_hash(body.confirmationToken)):
        raise HTTPException(status_code=403, detail="Confirmation token has already changed")
    payload = {"actionType": row.action_type, "parameters": row.parameters, "ownerId": row.owner_id, "tenantId": row.tenant_id, "sessionId": str(row.session_id)}
    if claims.get("action_hash") != row.action_hash or canonical_action_hash(payload) != row.action_hash:
        raise HTTPException(status_code=409, detail="Action draft changed")
    decision = await PolicyEngine().decide(subject, {"tenant_id": row.tenant_id, "classification": "Internal"}, "action:execute", "REQUEST_SUBMIT" if row.action_type.startswith("request") else "NOTIFICATION_UPDATE")
    if decision.decision.value != "ALLOW" or row.policy_version != subject.policy_version:
        raise HTTPException(status_code=403, detail="Action is no longer authorized")
    tool = default_mock_registry().get(row.action_type)
    result = await tool.handler(dict(row.parameters), subject)
    row.status = ActionStatus.COMPLETED.value
    row.consumed_at = datetime.now(timezone.utc)
    row.confirmation_token_hash = token_hash(f"consumed:{row.id}")
    row.result = {"execution": result}
    db.add(AuditEvent(tenant_id=row.tenant_id, event_type="ACTION_EXECUTED", actor_id=row.owner_id, policy_decision_id=decision.decision_id, payload={"actionId": str(row.id), "actionType": row.action_type}))
    await db.commit()
    return _preview(row, request_id)


@router.post("/mytasco/v1/aiwsp/actions/{action_id}/reject", operation_id="rejectAction")
async def reject_action(action_id: str, request_id: str = Depends(get_request_id), subject: SubjectContext = Depends(get_current_subject), db: AsyncSession = Depends(get_db)) -> ActionEnvelope:
    row = await _owned(db, action_id, subject, lock=True)
    if row.status == ActionStatus.WAITING_CONFIRMATION.value:
        row.status = ActionStatus.REJECTED.value
        row.confirmation_token_hash = token_hash(f"rejected:{row.id}")
        await db.commit()
    return _preview(row, request_id)
