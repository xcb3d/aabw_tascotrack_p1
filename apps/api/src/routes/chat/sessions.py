from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.dependencies import get_request_id, get_current_subject, get_db
from apps.api.src.db.models import Session
from apps.api.src.schemas.chat import CreateChatSessionRequest, SessionEnvelope, SessionBody
from modules.identity.src.subject import SubjectContext

router = APIRouter(tags=["Chat"])


@router.post("/mytasco/v1/aiwsp/chat/sessions", operation_id="createChatSession")
async def create_chat_session(
    body: CreateChatSessionRequest | None = None,
    subject: SubjectContext = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> SessionEnvelope:
    """Create an application-managed chat session."""
    session_id = uuid.uuid4()
    locale = body.locale if body else "vi-VN"
    title = body.title if body and body.title else "New Chat Session"
    
    user_uuid = uuid.UUID(subject.attributes["user_db_id"])
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    
    session_record = Session(
        id=session_id,
        user_id=user_uuid,
        principal_type="USER",
        status="ACTIVE",
        locale=locale,
        title=title,
        expires_at=expires_at
    )
    db.add(session_record)
    await db.commit()
    
    return SessionEnvelope(
        status="success",
        message="SUCCESS",
        requestId=request_id,
        body=SessionBody(
            sessionId=session_id,
            createdAt=datetime.now(timezone.utc),
            locale=locale
        )
    )