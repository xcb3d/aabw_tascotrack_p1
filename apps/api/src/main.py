from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from apps.api.src.config import get_settings
from apps.api.src.db.session import dispose_engine
from apps.api.src.dependencies import set_redis
from apps.api.src.middleware.app_code import AppCodeMiddleware
from apps.api.src.middleware.request_id import RequestIdMiddleware
from apps.api.src.routes.actions.actions import router as actions_router
from apps.api.src.routes.chat.runs import router as chat_runs_router
from apps.api.src.routes.chat.sessions import router as chat_sessions_router
from apps.api.src.routes.documents.documents import router as documents_router
from apps.api.src.routes.evaluation.evaluation import router as evaluation_router
from apps.api.src.routes.governance.governance import router as governance_router
from apps.api.src.routes.knowledge.search import router as knowledge_router
from apps.api.src.routes.legacy.index import router as legacy_index_router
from apps.api.src.routes.legacy.users import router as legacy_router
from apps.api.src.routes.system.auth import router as auth_router
from apps.api.src.routes.system.health import router as system_router
from apps.api.src.schemas.common import ErrorCode

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Manage shared infrastructure clients for the API process."""
    settings = get_settings()
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    set_redis(redis)
    # TODO: configure OpenTelemetry resource, tracer provider, and exporters.
    yield
    await redis.aclose()
    set_redis(None)
    await dispose_engine()


app = FastAPI(title="My Tasco Secure Agentic RAG API", version="1.0.0", lifespan=lifespan)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(AppCodeMiddleware)

app.include_router(auth_router)
app.include_router(system_router)
app.include_router(legacy_router)
app.include_router(legacy_index_router)
app.include_router(documents_router)
app.include_router(knowledge_router)
app.include_router(chat_sessions_router)
app.include_router(chat_runs_router)
app.include_router(actions_router)
app.include_router(governance_router)
app.include_router(evaluation_router)


@app.exception_handler(NotImplementedError)
async def not_implemented_handler(request: Request, exc: NotImplementedError) -> JSONResponse:
    """Return the OpenAPI error envelope for scaffold-only operations."""
    return JSONResponse(
        status_code=501,
        content={
            "status": "error",
            "code": ErrorCode.INTERNAL_ERROR.value,
            "message": str(exc),
            "requestId": getattr(request.state, "request_id", "unknown"),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return an error envelope without exposing internal exception details."""
    logger.exception("unhandled_request_error", request_id=getattr(request.state, "request_id", "unknown"))
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": ErrorCode.INTERNAL_ERROR.value,
            "message": "Internal server error",
            "requestId": getattr(request.state, "request_id", "unknown"),
        },
    )
