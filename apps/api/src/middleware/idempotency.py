from __future__ import annotations

import hashlib
import json
from redis.exceptions import RedisError

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from apps.api.src.dependencies import get_redis_client


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Replay successful mutation responses and reject key/payload conflicts."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        key = request.headers.get("Idempotency-Key")
        if not key or request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return await call_next(request)
        body = await request.body()
        scope = hashlib.sha256((request.headers.get("Authorization", "anonymous") + request.method + request.url.path).encode()).hexdigest()
        cache_key = f"idempotency:{scope}:{hashlib.sha256(key.encode()).hexdigest()}"
        request_hash = hashlib.sha256(body).hexdigest()
        try:
            redis = get_redis_client()
            cached = await redis.get(cache_key)
        except (RuntimeError, RedisError):
            return await call_next(request)
        if cached:
            value = json.loads(cached)
            if value.get("requestHash") != request_hash:
                return JSONResponse(status_code=409, content={"status": "error", "code": "conflict", "message": "Idempotency-Key was used with a different payload", "requestId": getattr(request.state, "request_id", "unknown")})
            return Response(content=value["body"].encode("latin1"), status_code=value["status"], media_type=value.get("mediaType"), headers={"X-Idempotent-Replay": "true"})
        response = await call_next(request)
        if response.status_code < 500 and response.media_type != "text/event-stream":
            body_iterator = getattr(response, "body_iterator")
            chunks = [chunk async for chunk in body_iterator]
            response_body = b"".join(chunk.encode() if isinstance(chunk, str) else chunk for chunk in chunks)
            value = {"requestHash": request_hash, "status": response.status_code, "mediaType": response.media_type or response.headers.get("content-type", "application/json").split(";", 1)[0], "body": response_body.decode("latin1")}
            await redis.setex(cache_key, 86400, json.dumps(value, separators=(",", ":")))
            headers = dict(response.headers)
            headers.pop("content-length", None)
            return Response(content=response_body, status_code=response.status_code, headers=headers, media_type=response.media_type)
        return response
