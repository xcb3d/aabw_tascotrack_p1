from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.db.models import Action, AgentRun as AgentRunRow, Job, RunEvent, Session
from apps.api.src.db.session import get_session_factory
from apps.api.src.dependencies import get_current_subject, get_db, get_request_id, require_idempotency_key
from apps.api.src.schemas.action import ActionPreview
from apps.api.src.schemas.chat import AgentRun, AgentRunEnvelope, AgentRunRequest, Citation, Claim
from apps.api.src.schemas.common import ActionStatus, AgentRoute, Confidence, PermissionDecision, RunStatus
from modules.identity.src.subject import SubjectContext

router = APIRouter(tags=["Chat"])


async def _envelope(db: AsyncSession, row: AgentRunRow, request_id: str) -> AgentRunEnvelope:
    action_row = (await db.execute(select(Action).where(Action.run_id == row.id))).scalar_one_or_none()
    action = None
    if action_row is not None:
        action = ActionPreview(
            actionId=action_row.id, actionType=action_row.action_type, status=ActionStatus(action_row.status),
            summary=action_row.summary, parameters=action_row.parameters, impact=action_row.impact,
            expiresAt=action_row.expires_at, confirmationToken=action_row.result.get("confirmationToken"),
        )
    return AgentRunEnvelope(
        body=AgentRun(
            runId=row.id, traceId=row.trace_id, sessionId=row.session_id, status=RunStatus(row.status),
            route=AgentRoute(row.route) if row.route else None, answer=row.answer,
            claims=[Claim.model_validate(item) for item in row.claims] if row.claims else None,
            citations=[Citation.model_validate(item) for item in row.citations] if row.citations else None,
            action=action, permissionDecision=PermissionDecision(row.permission_decision) if row.permission_decision else None,
            confidence=Confidence(row.confidence) if row.confidence else None, degradedReason=row.degraded_reason,
        ), requestId=request_id,
    )


@router.post("/mytasco/v1/aiwsp/chat/runs", operation_id="createAgentRun", status_code=202)
async def create_agent_run(
    body: AgentRunRequest,
    idempotency_key: str = Depends(require_idempotency_key),
    request_id: str = Depends(get_request_id),
    subject: SubjectContext = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
) -> AgentRunEnvelope:
    del idempotency_key
    session = await db.get(Session, body.sessionId)
    if session is None or session.tenant_id != subject.tenant_id or session.owner_id != subject.subject_id:
        raise HTTPException(status_code=404, detail="Session not found")
    existing = (await db.execute(select(AgentRunRow).where(AgentRunRow.tenant_id == subject.tenant_id, AgentRunRow.owner_id == subject.subject_id, AgentRunRow.client_request_id == body.clientRequestId))).scalar_one_or_none()
    if existing is not None:
        return await _envelope(db, existing, request_id)
    row = AgentRunRow(
        tenant_id=subject.tenant_id, owner_id=subject.subject_id, session_id=session.id,
        trace_id=uuid.uuid4(), client_request_id=body.clientRequestId, message=body.message,
        locale=body.locale, mode=body.mode.value, status=RunStatus.RECEIVED.value,
    )
    db.add(row)
    await db.flush()
    db.add(RunEvent(run_id=row.id, status=RunStatus.RECEIVED.value, payload={}))
    db.add(Job(queue="agent", job_type="agent_run", payload={
        "runId": str(row.id), "subject": {
            "tenant_id": subject.tenant_id, "subject_id": subject.subject_id,
            "roles": list(subject.roles), "departments": list(subject.departments),
            "managed_org_units": list(subject.managed_org_units), "attributes": subject.attributes,
            "session_id": subject.session_id, "step_up_level": subject.step_up_level,
            "step_up_expiry": subject.step_up_expiry.isoformat() if subject.step_up_expiry else None,
            "device_risk": subject.device_risk, "policy_version": subject.policy_version,
        },
    }))
    await db.commit()
    await db.refresh(row)
    return await _envelope(db, row, request_id)


async def _owned_run(db: AsyncSession, run_id: str, subject: SubjectContext) -> AgentRunRow:
    if db.in_transaction():
        await db.rollback()
    try:
        key = uuid.UUID(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    row = (await db.execute(select(AgentRunRow).where(AgentRunRow.id == key).execution_options(populate_existing=True))).scalar_one_or_none()
    if row is None or row.tenant_id != subject.tenant_id or row.owner_id != subject.subject_id:
        raise HTTPException(status_code=404, detail="Run not found")
    return row


@router.get("/mytasco/v1/aiwsp/chat/runs/{run_id}", operation_id="getAgentRun")
async def get_agent_run(run_id: str, request_id: str = Depends(get_request_id), subject: SubjectContext = Depends(get_current_subject), db: AsyncSession = Depends(get_db)) -> AgentRunEnvelope:
    return await _envelope(db, await _owned_run(db, run_id, subject), request_id)


@router.get("/mytasco/v1/aiwsp/chat/runs/{run_id}/events", operation_id="streamAgentRunEvents")
async def stream_agent_run_events(run_id: str, request: Request, subject: SubjectContext = Depends(get_current_subject), db: AsyncSession = Depends(get_db)) -> StreamingResponse:
    row = await _owned_run(db, run_id, subject)
    owned_run_id = row.id

    async def event_generator():
        last_id = 0
        terminal = {RunStatus.COMPLETED.value, RunStatus.INSUFFICIENT.value, RunStatus.DENIED.value, RunStatus.FAILED.value, RunStatus.CANCELLED.value, RunStatus.WAITING_CONFIRMATION.value}
        for _ in range(360):
            if await request.is_disconnected():
                return
            async with get_session_factory()() as polling:
                events = (await polling.execute(select(RunEvent).where(RunEvent.run_id == owned_run_id, RunEvent.id > last_id).order_by(RunEvent.id))).scalars().all()
                for event in events:
                    last_id = event.id
                    yield f"id: {event.id}\nevent: status\ndata: {json.dumps({'status': event.status, **event.payload})}\n\n"
                current = await polling.get(AgentRunRow, owned_run_id)
                assert current is not None
                final = {"runId": str(current.id), "status": current.status, "route": current.route, "answer": current.answer, "claims": current.claims, "citations": current.citations, "permissionDecision": current.permission_decision, "confidence": current.confidence}
            if current.status in terminal:
                yield f"event: final\ndata: {json.dumps(final, ensure_ascii=False)}\n\n"
                return
            await asyncio.sleep(0.25)
        yield "event: timeout\ndata: {}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.post("/mytasco/v1/aiwsp/chat/runs/{run_id}/cancel", operation_id="cancelAgentRun")
async def cancel_agent_run(run_id: str, request_id: str = Depends(get_request_id), subject: SubjectContext = Depends(get_current_subject), db: AsyncSession = Depends(get_db)) -> AgentRunEnvelope:
    row = await _owned_run(db, run_id, subject)
    if row.status not in {RunStatus.COMPLETED.value, RunStatus.DENIED.value, RunStatus.FAILED.value, RunStatus.CANCELLED.value, RunStatus.INSUFFICIENT.value}:
        row.cancelled = True
        row.status = RunStatus.CANCELLED.value
        db.add(RunEvent(run_id=row.id, status=row.status, payload={}))
        await db.commit()
    return await _envelope(db, row, request_id)
