from fastapi.testclient import TestClient


def test_knowledge_search_requires_authentication(client: TestClient) -> None:
    response = client.post("/mytasco/v1/aiwsp/knowledge/search", headers={"X-App-Code": "MYTASCO"}, json={"query": "test"})
    assert response.status_code == 401


def test_legacy_chat_requires_authentication(client: TestClient) -> None:
    response = client.post("/mytasco/v1/aiwsp/assistant/chat", headers={"X-App-Code": "MYTASCO"}, json={"message": "hello"})
    assert response.status_code == 401
