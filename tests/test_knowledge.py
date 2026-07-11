from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.skip(reason="TODO: implement knowledge search tests")
def test_search_knowledge_returns_501(client: TestClient) -> None:
    """POST /mytasco/v1/aiwsp/knowledge/search should return 501."""
    resp = client.post("/mytasco/v1/aiwsp/knowledge/search", json={"query": "test"})
    assert resp.status_code == 501


@pytest.mark.skip(reason="TODO: implement legacy chat tests")
def test_legacy_chat_returns_501(client: TestClient) -> None:
    """POST /mytasco/v1/aiwsp/assistant/chat should return 501."""
    resp = client.post("/mytasco/v1/aiwsp/assistant/chat", json={"message": "hello"})
    assert resp.status_code == 501