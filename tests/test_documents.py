from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.skip(reason="TODO: implement document endpoint tests")
def test_list_documents_returns_envelope(client: TestClient) -> None:
    """GET /mytasco/v1/aiwsp/documents should return a GenericEnvelope."""
    resp = client.get("/mytasco/v1/aiwsp/documents")
    assert resp.status_code == 501


@pytest.mark.skip(reason="TODO: implement document creation tests")
def test_create_document_requires_classification(client: TestClient) -> None:
    """POST /mytasco/v1/aiwsp/documents should reject missing classification."""
    resp = client.post("/mytasco/v1/aiwsp/documents")
    assert resp.status_code == 400