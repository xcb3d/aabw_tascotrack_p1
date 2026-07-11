from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.skip(reason="TODO: implement evaluation endpoint tests")
def test_run_public_evaluation_returns_501(client: TestClient) -> None:
    """POST /mytasco/v1/aiwsp/evaluation/public should return 501."""
    resp = client.post("/mytasco/v1/aiwsp/evaluation/public")
    assert resp.status_code == 501


@pytest.mark.skip(reason="TODO: implement evaluation run tests")
def test_create_evaluation_run_requires_dataset_id(client: TestClient) -> None:
    """POST /mytasco/v1/aiwsp/evaluations/runs should require datasetId."""
    resp = client.post("/mytasco/v1/aiwsp/evaluations/runs")
    assert resp.status_code == 422