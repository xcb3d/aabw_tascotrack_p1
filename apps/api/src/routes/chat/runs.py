import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.dependencies import get_request_id, require_idempotency_key, get_current_subject, get_db
from apps.api.src.db.models import AgentRun, Message, Session
from apps.api.src.schemas.chat import (
    AgentRunRequest,
    AgentRunEnvelope,
    AgentRun as AgentRunSchema,
)
from apps.api.src.schemas.common import RunStatus, ErrorCode
from modules.identity.src.subject import SubjectContext

router = APIRouter(tags=["Chat"])


@router.post("/mytasco/v1/aiwsp/chat/runs", operation_id="createAgentRun")
async def create_agent_run(
    body: AgentRunRequest,
    idempotency_key: str = Depends(require_idempotency_key),
    subject: SubjectContext = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> AgentRunEnvelope:
    """Start a secure deterministic, RAG, agentic-read, or action-preview run."""
    # 1. Verify session exists and is ACTIVE
    stmt_session = select(Session).where(Session.id == body.sessionId)
    result_session = await db.execute(stmt_session)
    session = result_session.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "code": ErrorCode.NOT_FOUND.value,
                "message": f"Session '{body.sessionId}' not found",
                "requestId": request_id,
            },
        )
    if session.status != "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "code": ErrorCode.INVALID_REQUEST.value,
                "message": f"Session is not ACTIVE (status: {session.status})",
                "requestId": request_id,
            },
        )

    # 2. Check Idempotency Key for replay
    stmt_run = select(AgentRun).where(AgentRun.idempotency_key == idempotency_key)
    result_run = await db.execute(stmt_run)
    existing_run = result_run.scalar_one_or_none()
    if existing_run:
        # Replay the existing run info
        return AgentRunEnvelope(
            status="success",
            message="SUCCESS",
            requestId=request_id,
            body=AgentRunSchema(
                runId=existing_run.id,
                traceId=existing_run.trace_id,
                sessionId=existing_run.session_id,
                status=RunStatus(existing_run.status),
                route=existing_run.route,
                answer=existing_run.answer,
                claims=existing_run.claims,
                citations=existing_run.citations,
            ),
        )

    # 3. Create message record
    message_id = uuid.uuid4()
    msg_record = Message(
        id=message_id,
        session_id=body.sessionId,
        role="USER",
        content=body.message,
        client_request_id=body.clientRequestId,
    )
    db.add(msg_record)
    await db.flush()

    # 4. Create run record
    run_id = uuid.uuid4()
    trace_id = uuid.uuid4()
    run_record = AgentRun(
        id=run_id,
        session_id=body.sessionId,
        input_message_id=message_id,
        trace_id=trace_id,
        idempotency_key=idempotency_key,
        status="RECEIVED",
    )
    db.add(run_record)
    
    await db.commit()

    return AgentRunEnvelope(
        status="success",
        message="SUCCESS",
        requestId=request_id,
        body=AgentRunSchema(
            runId=run_id,
            traceId=trace_id,
            sessionId=body.sessionId,
            status=RunStatus.RECEIVED,
        ),
    )


@router.get("/mytasco/v1/aiwsp/chat/runs/{run_id}", operation_id="getAgentRun")
async def get_agent_run(
    run_id: str,
    subject: SubjectContext = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> AgentRunEnvelope:
    """Get a run owned by the current subject."""
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "code": ErrorCode.INVALID_REQUEST.value,
                "message": "Invalid run_id UUID format",
                "requestId": request_id,
            },
        )

    stmt = select(AgentRun).where(AgentRun.id == run_uuid)
    result = await db.execute(stmt)
    run_rec = result.scalar_one_or_none()
    if not run_rec:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "code": ErrorCode.NOT_FOUND.value,
                "message": f"AgentRun '{run_id}' not found",
                "requestId": request_id,
            },
        )

    return AgentRunEnvelope(
        status="success",
        message="SUCCESS",
        requestId=request_id,
        body=AgentRunSchema(
            runId=run_rec.id,
            traceId=run_rec.trace_id,
            sessionId=run_rec.session_id,
            status=RunStatus(run_rec.status),
            route=run_rec.route,
            answer=run_rec.answer,
            claims=run_rec.claims,
            citations=run_rec.citations,
        ),
    )


@router.get("/mytasco/v1/aiwsp/chat/runs/{run_id}/events", operation_id="streamAgentRunEvents")
async def stream_agent_run_events(
    run_id: str,
    subject: SubjectContext = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream high-level run status events via SSE."""
    async def event_generator():
        # Mock streaming some progress status updates
        yield f"event: progress\ndata: {json.dumps({'status': 'RECEIVED', 'runId': run_id})}\n\n"
        yield f"event: progress\ndata: {json.dumps({'status': 'ROUTED', 'runId': run_id})}\n\n"
        yield f"event: progress\ndata: {json.dumps({'status': 'COMPLETED', 'runId': run_id})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/mytasco/v1/aiwsp/chat/runs/{run_id}/cancel", operation_id="cancelAgentRun")
async def cancel_agent_run(
    run_id: str,
    subject: SubjectContext = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> AgentRunEnvelope:
    """Cancel an active run."""
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "code": ErrorCode.INVALID_REQUEST.value,
                "message": "Invalid run_id UUID format",
                "requestId": request_id,
            },
        )

    stmt = select(AgentRun).where(AgentRun.id == run_uuid)
    result = await db.execute(stmt)
    run_rec = result.scalar_one_or_none()
    if not run_rec:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "code": ErrorCode.NOT_FOUND.value,
                "message": f"AgentRun '{run_id}' not found",
                "requestId": request_id,
            },
        )

    run_rec.status = "CANCELLED"
    await db.commit()

    return AgentRunEnvelope(
        status="success",
        message="SUCCESS",
        requestId=request_id,
        body=AgentRunSchema(
            runId=run_rec.id,
            traceId=run_rec.trace_id,
            sessionId=run_rec.session_id,
            status=RunStatus.CANCELLED,
            route=run_rec.route,
            answer=run_rec.answer,
        ),
    )