from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from jwt import PyJWTError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.config import Settings, get_settings
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
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> SubjectContext:
    """Resolve the authenticated subject from JWT.

    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    try:
        return resolve_subject(
            authorization[7:].strip(),
            secret=settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
        )
    except (PyJWTError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired Bearer token") from exc


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
    # Response replay and payload-conflict enforcement are handled by IdempotencyMiddleware.
    return idempotency_key
