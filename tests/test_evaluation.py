from fastapi.testclient import TestClient


def test_public_evaluation_requires_authentication(client: TestClient) -> None:
    response = client.post("/mytasco/v1/aiwsp/evaluation/public", headers={"X-App-Code": "MYTASCO"})
    assert response.status_code == 401


def test_create_evaluation_run_validates_request(client: TestClient) -> None:
    response = client.post("/mytasco/v1/aiwsp/evaluations/runs", headers={"X-App-Code": "MYTASCO"})
    assert response.status_code in {401, 422}
