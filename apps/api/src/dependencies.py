from __future__ import annotations

from collections.abc import AsyncGenerator
import dataclasses
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.config import Settings, get_settings
from apps.api.src.db.models import User
from apps.api.src.db.session import get_db_session
from apps.api.src.schemas.common import ErrorCode
from modules.identity.src.subject import SubjectContext, resolve_subject

# Redis client is process-scoped and initialized in app lifespan.
_redis: Redis | None = None


def set_redis(client: Redis | None) -> None:
    """Store the shared Redis client (called from lifespan)."""
    global _redis
    _redis = client


def get_redis_client() -> Redis:
    """Return the shared Redis client or raise if not initialized."""
    if _redis is None:
        raise RuntimeError("Redis client is not initialized")
    return _redis


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: async database session."""
    async for session in get_db_session():
        yield session


async def get_redis() -> Redis:
    """FastAPI dependency: shared Redis client."""
    return get_redis_client()


def get_request_id(request: Request) -> str:
    """Return the request id set by RequestIdMiddleware."""
    return getattr(request.state, "request_id", "unknown")


async def get_current_subject(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> SubjectContext:
    """Resolve the authenticated subject from JWT."""
    request_id = get_request_id(request)
    if authorization is None:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "code": ErrorCode.UNAUTHORIZED.value,
                "message": "Authorization header is missing",
                "requestId": request_id,
            },
        )
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "code": ErrorCode.UNAUTHORIZED.value,
                "message": "Invalid Authorization header. Expected Bearer <token>",
                "requestId": request_id,
            },
        )
    token = authorization.split(" ", 1)[1]
    try:
        subject = resolve_subject(token)
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "code": ErrorCode.UNAUTHORIZED.value,
                "message": f"Token verification failed: {str(e)}",
                "requestId": request_id,
            },
        )

    # Query DB to verify user exists and is active
    stmt = select(User).where(User.user_id == subject.subject_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "code": ErrorCode.UNAUTHORIZED.value,
                "message": f"User '{subject.subject_id}' not found in database",
                "requestId": request_id,
            },
        )
    if user.status != "Active":
        raise HTTPException(
            status_code=403,
            detail={
                "status": "error",
                "code": ErrorCode.FORBIDDEN.value,
                "message": f"User account is not active (status: {user.status})",
                "requestId": request_id,
            },
        )
    
    # Return a new SubjectContext using dataclasses.replace to respect frozen attribute
    new_attributes = dict(subject.attributes)
    new_attributes["user_db_id"] = str(user.id)
    return dataclasses.replace(subject, attributes=new_attributes)


async def require_idempotency_key(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    request_id: str = Depends(get_request_id),
) -> str:
    """Require Idempotency-Key header (min 16, max 128 chars per OpenAPI)."""
    if idempotency_key is None or not (16 <= len(idempotency_key) <= 128):
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "code": ErrorCode.INVALID_REQUEST.value,
                "message": "Idempotency-Key header is required (16-128 characters)",
                "requestId": request_id,
            },
        )
    # TODO: check Redis for prior response under this key and return cached result.
    return idempotency_key
