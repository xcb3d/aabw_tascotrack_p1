from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.skip(reason="TODO: implement action endpoint tests")
def test_get_action_preview_returns_501(client: TestClient) -> None:
    """GET /mytasco/v1/aiwsp/actions/{actionId} should return 501."""
    resp = client.get("/mytasco/v1/aiwsp/actions/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 501


@pytest.mark.skip(reason="TODO: implement confirm action tests")
def test_confirm_action_requires_idempotency_key(client: TestClient) -> None:
    """POST /mytasco/v1/aiwsp/actions/{actionId}/confirm should require Idempotency-Key."""
    resp = client.post(
        "/mytasco/v1/aiwsp/actions/00000000-0000-0000-0000-000000000000/confirm",
        json={"confirmationToken": "x" * 20},
    )
    assert resp.status_code == 400