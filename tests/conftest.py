from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.api.src.dependencies import set_redis


@pytest.fixture(autouse=True)
def _clear_redis() -> None:
    """Reset the shared Redis client between tests."""
    set_redis(None)


@pytest.fixture
def client():
    """FastAPI test client for integration-style endpoint tests."""
    from apps.api.src.main import app

    return TestClient(app)