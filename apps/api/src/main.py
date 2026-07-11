from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from apps.api.src.config import get_settings
from apps.api.src.db.session import dispose_engine
from apps.api.src.dependencies import set_redis
from apps.api.src.middleware.app_code import AppCodeMiddleware
from apps.api.src.middleware.request_id import RequestIdMiddleware
from apps.api.src.middleware.idempotency import IdempotencyMiddleware
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
_telemetry_configured = False


def configure_telemetry(settings) -> None:
    global _telemetry_configured
    if _telemetry_configured:
        return
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider

    provider = TracerProvider(resource=Resource.create({"service.name": "mytasco-secure-agentic-rag", "deployment.environment": settings.ENV}))
    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)))
    trace.set_tracer_provider(provider)
    structlog.configure(processors=[structlog.contextvars.merge_contextvars, structlog.processors.TimeStamper(fmt="iso"), structlog.processors.add_log_level, structlog.processors.JSONRenderer()])
    _telemetry_configured = True


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Manage shared infrastructure clients for the API process."""
    settings = get_settings()
    errors = settings.production_errors()
    if errors:
        raise RuntimeError("Invalid secure runtime configuration: " + "; ".join(errors))
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    set_redis(redis)
    configure_telemetry(settings)
    yield
    await redis.aclose()
    set_redis(None)
    await dispose_engine()


app = FastAPI(title="My Tasco Secure Agentic RAG API", version="1.0.0", lifespan=lifespan)
app.add_middleware(AppCodeMiddleware)
app.add_middleware(IdempotencyMiddleware)
app.add_middleware(RequestIdMiddleware)

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


def _error(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={
        "status": "error", "code": code, "message": message,
        "requestId": getattr(request.state, "request_id", "unknown"),
    })


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    mapping = {400: "invalid_request", 401: "unauthorized", 403: "forbidden", 404: "not_found", 409: "conflict", 410: "expired", 422: "invalid_request", 429: "rate_limited", 503: "service_unavailable"}
    return _error(request, exc.status_code, mapping.get(exc.status_code, "internal_error"), exc.detail if isinstance(exc.detail, str) else "Request failed")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    del exc
    return _error(request, 422, "invalid_request", "Request validation failed")


@app.exception_handler(NotImplementedError)
async def not_implemented_handler(request: Request, exc: NotImplementedError) -> JSONResponse:
    """Return the OpenAPI error envelope for scaffold-only operations."""
    return _error(request, 501, ErrorCode.INTERNAL_ERROR.value, str(exc))


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
