from fastapi.testclient import TestClient


def test_permission_explanation_requires_authentication(client: TestClient) -> None:
    response = client.get("/mytasco/v1/aiwsp/permissions/explain?documentId=test-doc", headers={"X-App-Code": "MYTASCO"})
    assert response.status_code == 401


def test_audit_requires_authentication(client: TestClient) -> None:
    response = client.get("/mytasco/v1/aiwsp/audit/recent", headers={"X-App-Code": "MYTASCO"})
    assert response.status_code == 401
