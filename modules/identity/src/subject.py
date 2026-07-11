from __future__ import annotations

from dataclasses import dataclass, field
import jwt
from apps.api.src.config import get_settings


@dataclass(frozen=True)
class SubjectContext:
    """Authenticated subject context made available to policy and services."""

    subject_id: str
    roles: tuple[str, ...] = ()
    departments: tuple[str, ...] = ()
    attributes: dict[str, str] = field(default_factory=dict)

def resolve_subject(token: str) -> SubjectContext:
    """Resolve a verified identity token to SubjectContext."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as e:
        raise ValueError(f"JWT verification failed: {str(e)}") from e

    subject_id = payload.get("sub") or payload.get("user_id")
    if not subject_id:
        raise ValueError("Missing subject ID claim ('sub' or 'user_id')")

    raw_roles = payload.get("roles", ())
    if isinstance(raw_roles, str):
        roles = (raw_roles,)
    else:
        roles = tuple(str(r) for r in raw_roles)

    raw_depts = payload.get("departments", ())
    if isinstance(raw_depts, str):
        departments = (raw_depts,)
    else:
        departments = tuple(str(d) for d in raw_depts)

    attributes = {}
    for k, v in payload.items():
        if k not in ("sub", "user_id", "roles", "departments", "exp", "iat"):
            attributes[k] = str(v)

    return SubjectContext(
        subject_id=str(subject_id),
        roles=roles,
        departments=departments,
        attributes=attributes,
    )
