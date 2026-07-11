from __future__ import annotations

from fastapi import APIRouter, Depends

from apps.api.src.dependencies import get_request_id, require_idempotency_key
from apps.api.src.schemas.action import ActionEnvelope, ConfirmActionRequest

router = APIRouter(tags=["Actions"])


@router.get("/mytasco/v1/aiwsp/actions/{action_id}", operation_id="getActionPreview")
async def get_action_preview(action_id: str) -> ActionEnvelope:
    """Get immutable action preview."""
    # TODO: load action preview from persistence.
    raise NotImplementedError("getActionPreview")


@router.post("/mytasco/v1/aiwsp/actions/{action_id}/confirm", operation_id="confirmAction")
async def confirm_action(
    action_id: str,
    body: ConfirmActionRequest,
    idempotency_key: str = Depends(require_idempotency_key),
    request_id: str = Depends(get_request_id),
) -> ActionEnvelope:
    """Confirm and execute an immutable action."""
    # TODO: verify confirmation token, execute action idempotently.
    raise NotImplementedError("confirmAction")


@router.post("/mytasco/v1/aiwsp/actions/{action_id}/reject", operation_id="rejectAction")
async def reject_action(
    action_id: str,
    request_id: str = Depends(get_request_id),
) -> ActionEnvelope:
    """Reject an action preview without upstream mutation."""
    # TODO: mark action as rejected.
    raise NotImplementedError("rejectAction")