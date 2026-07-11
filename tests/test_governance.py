from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.skip(reason="TODO: implement governance endpoint tests")
def test_explain_permission_returns_501(client: TestClient) -> None:
    """GET /mytasco/v1/aiwsp/permissions/explain should return 501."""
    resp = client.get("/mytasco/v1/aiwsp/permissions/explain?documentId=test-doc")
    assert resp.status_code == 501


@pytest.mark.skip(reason="TODO: implement audit endpoint tests")
def test_get_recent_audit_returns_501(client: TestClient) -> None:
    """GET /mytasco/v1/aiwsp/audit/recent should return 501."""
    resp = client.get("/mytasco/v1/aiwsp/audit/recent")
    assert resp.status_code == 501