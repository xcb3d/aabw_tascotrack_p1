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
    decision_id: str | None = None


class PolicyEngine:
    """In-process policy evaluator backed by versioned PostgreSQL snapshots."""

    async def decide(
        self,
        subject: SubjectContext,
        resource: dict[str, Any],
        action: str,
        purpose: str | None = None,
    ) -> PolicyDecision:
        """Evaluate deterministic tenant, lifecycle, classification and scope rules."""
        import uuid

        decision_id = str(uuid.uuid4())
        version = subject.policy_version
        if not subject.subject_id or not subject.tenant_id:
            return PolicyDecision(PermissionDecision.DENY, "INVALID_SUBJECT", version, decision_id)
        if resource.get("tenant_id") not in (None, subject.tenant_id):
            return PolicyDecision(PermissionDecision.DENY, "TENANT_MISMATCH", version, decision_id)
        if not action.startswith("admin:") and resource.get("status") in {"archived", "expired", "quarantined", "pending_classification"}:
            return PolicyDecision(PermissionDecision.DENY, "RESOURCE_NOT_ACTIVE", version, decision_id)
        if purpose == "SELF_PAYROLL_READ" and not subject.step_up_active:
            return PolicyDecision(PermissionDecision.DENY, "STEP_UP_REQUIRED", version, decision_id)
        if action.startswith("admin:") and not subject.is_admin:
            return PolicyDecision(PermissionDecision.DENY, "ADMIN_REQUIRED", version, decision_id)
        classification = str(resource.get("classification", "Internal"))
        department = resource.get("department_id") or resource.get("department")
        if classification == "Restricted" and "Executive" not in subject.roles:
            return PolicyDecision(PermissionDecision.DENY, "RESTRICTED_EXECUTIVE_ONLY", version, decision_id)
        if classification == "Confidential" and not subject.is_admin and department not in subject.departments:
            return PolicyDecision(PermissionDecision.DENY, "DEPARTMENT_SCOPE_REQUIRED", version, decision_id)
        allowed = resource.get("allowed_access") or ()
        if isinstance(allowed, str):
            allowed = (allowed,)
        if allowed and "All" not in allowed and not subject.is_admin:
            principals = {subject.subject_id, *subject.roles, *subject.departments}
            if not principals.intersection(set(allowed)):
                return PolicyDecision(PermissionDecision.DENY, "ACL_DENIED", version, decision_id)
        return PolicyDecision(PermissionDecision.ALLOW, "POLICY_ALLOW", version, decision_id)
