from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import jwt


@dataclass(frozen=True)
class SubjectContext:
    """Authenticated subject context made available to policy and services."""

    tenant_id: str
    subject_id: str
    roles: tuple[str, ...] = ()
    departments: tuple[str, ...] = ()
    managed_org_units: tuple[str, ...] = ()
    attributes: dict[str, str] = field(default_factory=dict)
    session_id: str | None = None
    authentication_time: datetime | None = None
    step_up_level: str = "NONE"
    step_up_expiry: datetime | None = None
    device_risk: str = "LOW"
    policy_version: str = "v1"

    @property
    def is_admin(self) -> bool:
        return bool({"Admin", "Executive"}.intersection(self.roles))

    @property
    def step_up_active(self) -> bool:
        return self.step_up_level in {"OTP", "STRONG"} and (
            self.step_up_expiry is None or self.step_up_expiry > datetime.now(timezone.utc)
        )


def _tuple_claim(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(",") if part.strip())
    if isinstance(value, (list, tuple)) and all(isinstance(item, str) for item in value):
        return tuple(value)
    return ()


def _timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def resolve_subject(
    token: str,
    *,
    secret: str,
    algorithm: str = "HS256",
    issuer: str | None = None,
    audience: str | None = None,
) -> SubjectContext:
    """Validate a JWT and map authoritative claims to a fail-closed context."""
    claims = jwt.decode(
        token,
        secret,
        algorithms=[algorithm],
        issuer=issuer,
        audience=audience,
        options={"require": ["exp", "iat", "sub", "tenant_id"]},
    )
    roles = _tuple_claim(claims.get("roles"))
    departments = _tuple_claim(claims.get("departments") or claims.get("department_id"))
    raw_attributes = claims.get("attributes")
    attributes: dict[Any, Any] = raw_attributes if isinstance(raw_attributes, dict) else {}
    return SubjectContext(
        tenant_id=str(claims["tenant_id"]),
        subject_id=str(claims["sub"]),
        roles=roles,
        departments=departments,
        managed_org_units=_tuple_claim(claims.get("managed_org_units")),
        attributes={str(key): str(value) for key, value in attributes.items()},
        session_id=str(claims["sid"]) if claims.get("sid") else None,
        authentication_time=_timestamp(claims.get("auth_time") or claims.get("iat")),
        step_up_level=str(claims.get("step_up_level", "NONE")).upper(),
        step_up_expiry=_timestamp(claims.get("step_up_expiry")),
        device_risk=str(claims.get("device_risk", "LOW")).upper(),
        policy_version=str(claims.get("policy_version", "v1")),
    )
