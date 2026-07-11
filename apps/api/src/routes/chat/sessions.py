from __future__ import annotations

from fastapi import APIRouter, Depends

from apps.api.src.dependencies import get_request_id
from apps.api.src.schemas.chat import CreateChatSessionRequest, SessionEnvelope
from apps.api.src.schemas.envelope import GenericEnvelope

router = APIRouter(tags=["Chat"])


@router.post("/mytasco/v1/aiwsp/chat/sessions", operation_id="createChatSession")
async def create_chat_session(
    body: CreateChatSessionRequest | None = None,
    request_id: str = Depends(get_request_id),
) -> SessionEnvelope:
    """Create an application-managed chat session."""
    # TODO: persist session record and return created session.
    raise NotImplementedError("createChatSession")