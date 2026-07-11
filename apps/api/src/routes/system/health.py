from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.config import get_settings
from apps.api.src.dependencies import get_db, get_redis, get_request_id
from apps.api.src.schemas.envelope import HealthBody, HealthEnvelope

router = APIRouter(tags=["System"])


@router.get(
    "/health",
    operation_id="getHealth",
    response_model=HealthEnvelope,
    responses={503: {"description": "Required secure dependency unavailable"}},
)
async def get_health(
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    request_id: str = Depends(get_request_id),
) -> HealthEnvelope:
    """getHealth — GET /health

    Probe Postgres (`SELECT 1` + inventory counts) and Redis (`PING`).
    Returns COP HealthEnvelope; sets HTTP 503 when a dependency is down.
    """
    settings = get_settings()
    documents_count = 0
    chunks_count = 0
    users_count = 0
    openai_configured = bool(settings.OPENAI_API_KEY)
    retriever_status: dict = {}
    ok = True

    try:
        await db.execute(text("SELECT 1"))
        try:
            result = await db.execute(text("SELECT COUNT(*) FROM documents"))
            documents_count = int(result.scalar() or 0)
            result = await db.execute(text("SELECT COUNT(*) FROM chunks"))
            chunks_count = int(result.scalar() or 0)
        except Exception:
            # Tables may not exist yet during scaffold smoke tests.
            retriever_status["inventory"] = "tables_unavailable"
        retriever_status["postgres"] = "ok"
    except Exception as exc:  # noqa: BLE001 — health probe must never raise
        ok = False
        retriever_status["postgres"] = f"error: {type(exc).__name__}"

    try:
        await redis.ping()
        retriever_status["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001 — health probe must never raise
        ok = False
        retriever_status["redis"] = f"error: {type(exc).__name__}"

    if not ok:
        response.status_code = 503

    return HealthEnvelope(
        body=HealthBody(
            ok=ok,
            documents=documents_count,
            chunks=chunks_count,
            users=users_count,
            openaiConfigured=openai_configured,
            retriever=retriever_status,
        ),
        requestId=request_id,
    )
