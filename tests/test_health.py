from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.dependencies import get_db, get_redis
from apps.api.src.main import app


def _make_db(side_effect: Exception | None = None) -> AsyncMock:
    mock_db = AsyncMock(spec=AsyncSession)
    if side_effect is not None:
        mock_db.execute = AsyncMock(side_effect=side_effect)
        return mock_db

    mock_result = MagicMock()
    mock_result.scalar.return_value = 0
    mock_db.execute = AsyncMock(return_value=mock_result)
    return mock_db


def _make_redis(side_effect: Exception | None = None) -> AsyncMock:
    mock_redis = AsyncMock()
    if side_effect is not None:
        mock_redis.ping = AsyncMock(side_effect=side_effect)
    else:
        mock_redis.ping = AsyncMock(return_value=True)
    return mock_redis


def test_health_returns_success_when_deps_up() -> None:
    """Health should return 200 with ok=true when both Postgres and Redis are reachable."""
    mock_db = _make_db()
    mock_redis = _make_redis()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield mock_db  # type: ignore[misc]

    async def override_get_redis() -> AsyncMock:
        return mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    try:
        with TestClient(app) as client:
            resp = client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["message"] == "SUCCESS"
    assert data["body"]["ok"] is True
    assert "documents" in data["body"]
    assert "chunks" in data["body"]
    assert "users" in data["body"]
    assert "openaiConfigured" in data["body"]
    assert "retriever" in data["body"]
    assert data["requestId"]


def test_health_returns_503_when_postgres_down() -> None:
    """Health should return 503 when PostgreSQL is unreachable."""
    mock_db = _make_db(side_effect=Exception("connection refused"))
    mock_redis = _make_redis()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield mock_db  # type: ignore[misc]

    async def override_get_redis() -> AsyncMock:
        return mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    try:
        with TestClient(app) as client:
            resp = client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "success"
    assert data["body"]["ok"] is False
