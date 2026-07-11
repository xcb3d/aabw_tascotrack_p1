from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.api.src.schemas.common import PermissionDecision
from modules.identity.src.subject import SubjectContext


@dataclass(frozen=True)
class PolicyDecision:
    decision: PermissionDecision
    reason: str
    policy_version: str | None = None


class PolicyEngine:
    """In-process policy evaluator backed by versioned PostgreSQL snapshots."""

    async def decide(
        self,
        subject: SubjectContext,
        resource: dict[str, Any],
        action: str,
    ) -> PolicyDecision:
        """Decide whether subject may perform an action on a resource.

        # TODO: load cached versioned policy snapshot and evaluate RBAC/ABAC rules.
        """
        raise NotImplementedError("PolicyEngine.decide")
