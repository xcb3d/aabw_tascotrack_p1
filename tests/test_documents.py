from fastapi.testclient import TestClient


def test_list_documents_requires_authentication(client: TestClient) -> None:
    response = client.get("/mytasco/v1/aiwsp/documents", headers={"X-App-Code": "MYTASCO"})
    assert response.status_code == 401


def test_create_document_rejects_missing_form(client: TestClient) -> None:
    response = client.post("/mytasco/v1/aiwsp/documents", headers={"X-App-Code": "MYTASCO"})
    assert response.status_code in {400, 401, 422}
