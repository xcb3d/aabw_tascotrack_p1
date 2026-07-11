from fastapi.testclient import TestClient


def test_action_preview_requires_app_auth(client: TestClient) -> None:
    response = client.get("/mytasco/v1/aiwsp/actions/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 401
    assert response.json()["status"] == "error"


def test_confirm_action_requires_idempotency_key(client: TestClient) -> None:
    response = client.post("/mytasco/v1/aiwsp/actions/00000000-0000-0000-0000-000000000000/confirm", headers={"X-App-Code": "MYTASCO"}, json={"confirmationToken": "x" * 20})
    assert response.status_code in {400, 401}
