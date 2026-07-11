from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.skip(reason="TODO: implement chat session tests")
def test_create_chat_session_returns_201(client: TestClient) -> None:
    """POST /mytasco/v1/aiwsp/chat/sessions should return SessionEnvelope."""
    resp = client.post("/mytasco/v1/aiwsp/chat/sessions")
    assert resp.status_code == 501


@pytest.mark.skip(reason="TODO: implement agent run tests")
def test_create_agent_run_requires_idempotency_key(client: TestClient) -> None:
    """POST /mytasco/v1/aiwsp/chat/runs should require Idempotency-Key header."""
    resp = client.post(
        "/mytasco/v1/aiwsp/chat/runs",
        json={"sessionId": "00000000-0000-0000-0000-000000000000", "message": "hello", "clientRequestId": "00000000-0000-0000-0000-000000000000"},
    )
    assert resp.status_code == 400