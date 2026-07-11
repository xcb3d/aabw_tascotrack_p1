from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.config import Settings
from modules.agent.src.runtime import execute_run
from modules.identity.src.subject import SubjectContext


def subject_from_payload(value: dict) -> SubjectContext:
    expiry = datetime.fromisoformat(value["step_up_expiry"]) if value.get("step_up_expiry") else None
    return SubjectContext(
        tenant_id=str(value["tenant_id"]), subject_id=str(value["subject_id"]),
        roles=tuple(value.get("roles") or ()), departments=tuple(value.get("departments") or ()),
        managed_org_units=tuple(value.get("managed_org_units") or ()), attributes=dict(value.get("attributes") or {}),
        session_id=value.get("session_id"), step_up_level=str(value.get("step_up_level", "NONE")),
        step_up_expiry=expiry, device_risk=str(value.get("device_risk", "LOW")),
        policy_version=str(value.get("policy_version", "v1")),
    )


async def run_agent_job(session: AsyncSession, run_id: str, subject_payload: dict, settings: Settings) -> None:
    await execute_run(session, uuid.UUID(run_id), subject_from_payload(subject_payload), settings)
    await session.commit()
