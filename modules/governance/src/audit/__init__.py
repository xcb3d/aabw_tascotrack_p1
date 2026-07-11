from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.db.models import AuditEvent


_FORBIDDEN_KEYS = {"prompt", "content", "evidence", "token", "password", "secret", "raw"}


async def append_audit(session: AsyncSession, event_type: str, payload: dict[str, Any], *, tenant_id: str, actor_id: str | None = None, request_id: str | None = None, trace_id: str | None = None, policy_decision_id: str | None = None) -> AuditEvent:
    if any(any(word in key.casefold() for word in _FORBIDDEN_KEYS) for key in payload):
        raise ValueError("audit payload contains a forbidden content-bearing key")
    row = AuditEvent(tenant_id=tenant_id, event_type=event_type, actor_id=actor_id, request_id=request_id, trace_id=trace_id, policy_decision_id=policy_decision_id, payload=payload)
    session.add(row)
    await session.flush()
    return row
