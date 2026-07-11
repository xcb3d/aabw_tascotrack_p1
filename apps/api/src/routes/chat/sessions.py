from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.db.models import Session
from apps.api.src.dependencies import get_current_subject, get_db, get_request_id
from apps.api.src.schemas.chat import CreateChatSessionRequest, SessionBody, SessionEnvelope
from modules.identity.src.subject import SubjectContext

router = APIRouter(tags=["Chat"])


@router.post("/mytasco/v1/aiwsp/chat/sessions", operation_id="createChatSession", status_code=201)
async def create_chat_session(
    body: CreateChatSessionRequest | None = None,
    request_id: str = Depends(get_request_id),
    subject: SubjectContext = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
) -> SessionEnvelope:
    value = body or CreateChatSessionRequest()
    row = Session(tenant_id=subject.tenant_id, owner_id=subject.subject_id, locale=value.locale, title=value.title)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return SessionEnvelope(body=SessionBody(sessionId=row.id, createdAt=row.created_at, locale=row.locale), requestId=request_id)
