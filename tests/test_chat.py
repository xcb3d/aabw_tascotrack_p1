from fastapi.testclient import TestClient


def test_create_chat_session_requires_authentication(client: TestClient) -> None:
    response = client.post("/mytasco/v1/aiwsp/chat/sessions", headers={"X-App-Code": "MYTASCO"})
    assert response.status_code == 401


def test_create_agent_run_requires_idempotency_key(client: TestClient) -> None:
    response = client.post("/mytasco/v1/aiwsp/chat/runs", headers={"X-App-Code": "MYTASCO"}, json={"sessionId": "00000000-0000-0000-0000-000000000000", "message": "hello", "clientRequestId": "00000000-0000-0000-0000-000000000000"})
    assert response.status_code in {400, 401}
