import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.dependencies import get_request_id, require_idempotency_key, get_current_subject, get_db
from apps.api.src.db.models import Action
from apps.api.src.schemas.action import ActionEnvelope, ConfirmActionRequest, ActionPreview
from apps.api.src.schemas.common import ErrorCode, ActionStatus
from modules.identity.src.subject import SubjectContext

router = APIRouter(tags=["Actions"])


@router.get("/mytasco/v1/aiwsp/actions/{action_id}", operation_id="getActionPreview")
async def get_action_preview(
    action_id: str,
    subject: SubjectContext = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> ActionEnvelope:
    """Get immutable action preview."""
    try:
        action_uuid = uuid.UUID(action_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "code": ErrorCode.INVALID_REQUEST.value,
                "message": "Invalid action_id UUID format",
                "requestId": request_id,
            },
        )

    stmt = select(Action).where(Action.id == action_uuid)
    result = await db.execute(stmt)
    act = result.scalar_one_or_none()
    if not act:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "code": ErrorCode.NOT_FOUND.value,
                "message": f"Action '{action_id}' not found",
                "requestId": request_id,
            },
        )

    return ActionEnvelope(
        status="success",
        message="SUCCESS",
        requestId=request_id,
        body=ActionPreview(
            actionId=act.id,
            actionType=act.action_type,
            status=ActionStatus(act.status),
            summary=act.summary,
            parameters=act.parameters,
            expiresAt=act.expires_at,
        ),
    )


@router.post("/mytasco/v1/aiwsp/actions/{action_id}/confirm", operation_id="confirmAction")
async def confirm_action(
    action_id: str,
    body: ConfirmActionRequest,
    idempotency_key: str = Depends(require_idempotency_key),
    subject: SubjectContext = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> ActionEnvelope:
    """Confirm and execute an immutable action."""
    try:
        action_uuid = uuid.UUID(action_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "code": ErrorCode.INVALID_REQUEST.value,
                "message": "Invalid action_id UUID format",
                "requestId": request_id,
            },
        )

    stmt = select(Action).where(Action.id == action_uuid)
    result = await db.execute(stmt)
    act = result.scalar_one_or_none()
    if not act:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "code": ErrorCode.NOT_FOUND.value,
                "message": f"Action '{action_id}' not found",
                "requestId": request_id,
            },
        )

    if act.status != "WAITING_CONFIRMATION" and act.status != "DRAFT":
         raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "code": ErrorCode.INVALID_REQUEST.value,
                "message": f"Action is not in a confirmable status (status: {act.status})",
                "requestId": request_id,
            },
        )

    act.status = "COMPLETED"
    act.consumed_at = datetime.now(timezone.utc)
    act.idempotency_key = idempotency_key
    await db.commit()

    return ActionEnvelope(
        status="success",
        message="SUCCESS",
        requestId=request_id,
        body=ActionPreview(
            actionId=act.id,
            actionType=act.action_type,
            status=ActionStatus.COMPLETED,
            summary=act.summary,
            parameters=act.parameters,
            expiresAt=act.expires_at,
        ),
    )


@router.post("/mytasco/v1/aiwsp/actions/{action_id}/reject", operation_id="rejectAction")
async def reject_action(
    action_id: str,
    subject: SubjectContext = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> ActionEnvelope:
    """Reject an action preview without upstream mutation."""
    try:
        action_uuid = uuid.UUID(action_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "code": ErrorCode.INVALID_REQUEST.value,
                "message": "Invalid action_id UUID format",
                "requestId": request_id,
            },
        )

    stmt = select(Action).where(Action.id == action_uuid)
    result = await db.execute(stmt)
    act = result.scalar_one_or_none()
    if not act:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "code": ErrorCode.NOT_FOUND.value,
                "message": f"Action '{action_id}' not found",
                "requestId": request_id,
            },
        )

    act.status = "REJECTED"
    act.consumed_at = datetime.now(timezone.utc)
    await db.commit()

    return ActionEnvelope(
        status="success",
        message="SUCCESS",
        requestId=request_id,
        body=ActionPreview(
            actionId=act.id,
            actionType=act.action_type,
            status=ActionStatus.REJECTED,
            summary=act.summary,
            parameters=act.parameters,
            expiresAt=act.expires_at,
        ),
    )