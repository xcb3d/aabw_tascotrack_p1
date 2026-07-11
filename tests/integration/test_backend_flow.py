from __future__ import annotations

import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from apps.api.src.config import get_settings
from apps.api.src.main import app


pytestmark = [
    pytest.mark.integration,
    pytest.mark.filterwarnings("ignore::jwt.warnings.InsecureKeyLengthWarning"),
]


def _drain_worker() -> None:
    worker = subprocess.run([sys.executable, "-c", "import asyncio\nfrom apps.worker.src.consumer import process_one\nfrom apps.api.src.db.session import dispose_engine\nasync def main():\n    try:\n        while await process_one():\n            pass\n    finally:\n        await dispose_engine()\nasyncio.run(main())"], check=False, capture_output=True, text=True)
    assert worker.returncode == 0, worker.stderr


def _wait_for_status(client: TestClient, run_id: str, status: str):
    response = None
    for _ in range(20):
        response = client.get(f"/mytasco/v1/aiwsp/chat/runs/{run_id}", headers=_headers())
        if response.json()["body"]["status"] == status:
            return response
        time.sleep(0.1)
    assert response is not None
    return response


def _headers(*, idempotent: bool = False) -> dict[str, str]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    token = jwt.encode({
        "sub": "integration-admin", "tenant_id": "integration-tenant",
        "roles": ["Admin"], "departments": ["HR"],
        "iss": settings.JWT_ISSUER, "aud": settings.JWT_AUDIENCE,
        "iat": now, "exp": now + timedelta(minutes=10),
        "policy_version": "v1",
    }, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    result = {"X-App-Code": settings.APP_CODE, "Authorization": f"Bearer {token}"}
    if idempotent:
        result["Idempotency-Key"] = uuid.uuid4().hex
    return result


def test_deterministic_run_reaches_completed() -> None:
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["body"]["retriever"] == {"postgres": "ok", "redis": "ok"}
        session_response = client.post("/mytasco/v1/aiwsp/chat/sessions", headers=_headers(), json={"locale": "vi-VN"})
        assert session_response.status_code == 201, session_response.text
        session_id = session_response.json()["body"]["sessionId"]
        run_headers = _headers(idempotent=True)
        run_payload = {"sessionId": session_id, "message": "Cho tôi xem chấm công", "clientRequestId": str(uuid.uuid4())}
        run_response = client.post("/mytasco/v1/aiwsp/chat/runs", headers=run_headers, json=run_payload)
        assert run_response.status_code == 202, run_response.text
        replay = client.post("/mytasco/v1/aiwsp/chat/runs", headers=run_headers, json=run_payload)
        assert replay.status_code == 202
        assert replay.headers["X-Idempotent-Replay"] == "true"
        assert replay.json() == run_response.json()
        conflicting = client.post("/mytasco/v1/aiwsp/chat/runs", headers=run_headers, json={**run_payload, "message": "different payload"})
        assert conflicting.status_code == 409
        run_id = run_response.json()["body"]["runId"]
        _drain_worker()
        completed = _wait_for_status(client, run_id, "COMPLETED")
        assert completed.status_code == 200, completed.text
        assert completed.json()["body"]["status"] == "COMPLETED"
        assert completed.json()["body"]["route"] == "DETERMINISTIC"
        events = client.get(f"/mytasco/v1/aiwsp/chat/runs/{run_id}/events", headers=_headers())
        assert events.status_code == 200
        assert "event: final" in events.text
        assert '"status": "COMPLETED"' in events.text


def test_ingestion_search_rag_and_confirmed_action() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/mytasco/v1/aiwsp/documents", headers=_headers(idempotent=True),
            files={"file": ("leave.md", "# Chính sách nghỉ phép\nNhân viên có 12 ngày nghỉ phép mỗi năm.", "text/markdown")},
            data={"title": "Chính sách nghỉ phép", "departmentId": "HR", "classification": "Internal", "allowedAccess": "All"},
        )
        assert created.status_code == 202, created.text
        document_id = created.json()["body"]["documentId"]
        _drain_worker()
        published = client.post(f"/mytasco/v1/aiwsp/documents/{document_id}/publish", headers=_headers(idempotent=True))
        assert published.status_code == 200, published.text
        search = client.post("/mytasco/v1/aiwsp/knowledge/search", headers=_headers(), json={"query": "nghỉ phép"})
        assert search.status_code == 200, search.text
        assert search.json()["body"]["result"]
        chat = client.post("/mytasco/v1/aiwsp/assistant/chat", headers=_headers(), json={"message": "Chính sách nghỉ phép là gì?"})
        assert chat.status_code == 200, chat.text
        assert chat.json()["body"]["answer"]
        assert chat.json()["body"]["citations"]

        new_version = client.post(
            f"/mytasco/v1/aiwsp/documents/{document_id}/versions", headers=_headers(idempotent=True),
            files={"file": ("leave-v2.md", "# Chính sách nghỉ phép\nNhân viên có 15 ngày nghỉ phép mỗi năm.", "text/markdown")},
        )
        assert new_version.status_code == 202, new_version.text
        _drain_worker()
        replacement = client.post(f"/mytasco/v1/aiwsp/documents/{document_id}/publish", headers=_headers(idempotent=True))
        assert replacement.status_code == 200
        assert replacement.json()["body"]["versionId"] == new_version.json()["body"]["versionId"]

        malformed = client.post(
            "/mytasco/v1/aiwsp/documents", headers=_headers(idempotent=True),
            files={"file": ("bad.md", b"\xff\xfe", "text/markdown")},
            data={"title": "Malformed", "departmentId": "HR", "classification": "Internal"},
        )
        assert malformed.status_code == 400

        blocked = client.post(
            "/mytasco/v1/aiwsp/documents", headers=_headers(idempotent=True),
            files={"file": ("secret.md", "# Unsafe\nAuthorization: Bearer secret-token", "text/markdown")},
            data={"title": "Unsafe", "departmentId": "HR", "classification": "Internal"},
        )
        assert blocked.status_code == 202
        _drain_worker()
        blocked_publish = client.post(f"/mytasco/v1/aiwsp/documents/{blocked.json()['body']['documentId']}/publish", headers=_headers(idempotent=True))
        assert blocked_publish.status_code == 409

        session_id = client.post("/mytasco/v1/aiwsp/chat/sessions", headers=_headers(), json={}).json()["body"]["sessionId"]
        run = client.post("/mytasco/v1/aiwsp/chat/runs", headers=_headers(idempotent=True), json={"sessionId": session_id, "message": "Gửi đơn này", "mode": "action_preview", "clientRequestId": str(uuid.uuid4())})
        assert run.status_code == 202, run.text
        run_id = run.json()["body"]["runId"]
        _drain_worker()
        preview = _wait_for_status(client, run_id, "WAITING_CONFIRMATION")
        assert preview.json()["body"]["status"] == "WAITING_CONFIRMATION"
        action = preview.json()["body"]["action"]
        confirmed = client.post(f"/mytasco/v1/aiwsp/actions/{action['actionId']}/confirm", headers=_headers(idempotent=True), json={"confirmationToken": action["confirmationToken"]})
        assert confirmed.status_code == 200, confirmed.text
        assert confirmed.json()["body"]["status"] == "COMPLETED"
