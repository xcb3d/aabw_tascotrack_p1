from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from apps.api.src.config import get_settings
from apps.api.src.schemas.common import ErrorCode

APP_CODE_HEADER = "X-App-Code"
# Paths that skip App-Code enforcement (health is public).
SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class AppCodeMiddleware(BaseHTTPMiddleware):
    """Reject requests whose X-App-Code is not MYTASCO (except /health)."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        settings = get_settings()
        app_code = request.headers.get(APP_CODE_HEADER)
        if app_code != settings.APP_CODE:
            request_id = getattr(request.state, "request_id", "unknown")
            return JSONResponse(
                status_code=401,
                content={
                    "status": "error",
                    "code": ErrorCode.UNAUTHORIZED.value,
                    "message": f"Missing or invalid {APP_CODE_HEADER}",
                    "requestId": request_id,
                },
            )
        return await call_next(request)
