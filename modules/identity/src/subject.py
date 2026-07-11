from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SubjectContext:
    """Authenticated subject context made available to policy and services."""

    subject_id: str
    roles: tuple[str, ...] = ()
    departments: tuple[str, ...] = ()
    attributes: dict[str, str] = field(default_factory=dict)


def resolve_subject(token: str) -> SubjectContext:
    """Resolve a verified identity token to SubjectContext.

    # TODO: validate JWT claims and map IAM attributes.
    """
    raise NotImplementedError("resolve_subject")
