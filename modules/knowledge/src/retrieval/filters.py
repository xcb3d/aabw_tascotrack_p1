"""Synthetic-corpus authorization bootstrap for AIE2 retrieval tests."""

from __future__ import annotations

from dataclasses import dataclass

DEPARTMENT_ALIASES = {
    "human resources": "hr",
    "nhân sự": "hr",
    "hr": "hr",
}


def canonical_department(value: str) -> str:
    normalized = value.strip().casefold()
    return DEPARTMENT_ALIASES.get(normalized, normalized)


@dataclass(frozen=True)
class RetrievalSubject:
    tenant_id: str
    user_id: str
    department: str
    role: str


def can_read_chunk(
    subject: RetrievalSubject,
    *,
    tenant_id: str,
    department: str,
    classification: str,
    allowed_access: str,
) -> bool:
    """Apply the workbook's demo permission matrix as a hard predicate."""

    if subject.tenant_id != tenant_id:
        return False
    if classification == "Secret":
        return False
    is_executive = subject.role.casefold() == "executive"
    if classification == "Restricted" and not is_executive:
        return False
    if classification == "Confidential" and not (
        is_executive or canonical_department(subject.department) == canonical_department(department)
    ):
        return False
    if allowed_access == "Executive Only" and not is_executive:
        return False
    if allowed_access == "Own Department" and not (
        is_executive or canonical_department(subject.department) == canonical_department(department)
    ):
        return False
    return allowed_access in {"All", "All Employees", "Own Department", "Executive Only"}
