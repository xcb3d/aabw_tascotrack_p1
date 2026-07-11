from __future__ import annotations

from typing import Any

from modules.identity.src.subject import SubjectContext
from modules.tools.src.registry import ToolDefinition, ToolRegistry


async def _attendance(arguments: dict[str, Any], subject: SubjectContext) -> dict[str, Any]:
    del arguments
    return {"subjectId": subject.subject_id, "month": "current", "presentDays": 20, "lateCount": 1}


async def _payroll(arguments: dict[str, Any], subject: SubjectContext) -> dict[str, Any]:
    del arguments
    if not subject.step_up_active:
        raise PermissionError("STEP_UP_REQUIRED")
    return {"subjectId": subject.subject_id, "period": "current", "netSalary": 25_000_000, "currency": "VND"}


async def _request_get(arguments: dict[str, Any], subject: SubjectContext) -> dict[str, Any]:
    return {"requestId": str(arguments.get("requestId", "REQ-DEMO-001")), "ownerId": subject.subject_id, "status": "PENDING"}


async def _request_search(arguments: dict[str, Any], subject: SubjectContext) -> dict[str, Any]:
    del arguments
    return {"ownerId": subject.subject_id, "requests": [{"requestId": "REQ-DEMO-001", "status": "PENDING"}]}


async def _notifications(arguments: dict[str, Any], subject: SubjectContext) -> dict[str, Any]:
    del arguments
    return {"subjectId": subject.subject_id, "unreadCount": 3}


async def _staff(arguments: dict[str, Any], subject: SubjectContext) -> dict[str, Any]:
    return {"query": str(arguments.get("query", "")), "tenantId": subject.tenant_id, "results": []}


async def _org_scope(arguments: dict[str, Any], subject: SubjectContext) -> dict[str, Any]:
    del arguments
    return {"subjectId": subject.subject_id, "managedOrgUnits": list(subject.managed_org_units)}


async def _news(arguments: dict[str, Any], subject: SubjectContext) -> dict[str, Any]:
    del arguments, subject
    return {"items": []}


async def _draft(arguments: dict[str, Any], subject: SubjectContext) -> dict[str, Any]:
    return {"ownerId": subject.subject_id, "draft": dict(arguments)}


async def _submit(arguments: dict[str, Any], subject: SubjectContext) -> dict[str, Any]:
    return {"ownerId": subject.subject_id, "requestId": str(arguments.get("requestId", "REQ-DEMO-NEW")), "status": "SUBMITTED"}


async def _mark_read(arguments: dict[str, Any], subject: SubjectContext) -> dict[str, Any]:
    return {"ownerId": subject.subject_id, "notificationId": str(arguments.get("notificationId", "all")), "status": "READ"}


def default_mock_registry() -> ToolRegistry:
    registry = ToolRegistry()
    definitions = (
        ("attendance_get_self_summary", "READ", "SELF_ATTENDANCE_READ", "NONE", "Confidential", _attendance),
        ("payroll_get_self_step_up", "READ", "SELF_PAYROLL_READ", "OTP", "Restricted", _payroll),
        ("request_get_self", "READ", "SELF_REQUEST_READ", "NONE", "Internal", _request_get),
        ("request_search_self", "READ", "SELF_REQUEST_READ", "NONE", "Internal", _request_search),
        ("notification_count_unread", "READ", "NOTIFICATION_UPDATE", "NONE", "Internal", _notifications),
        ("staff_search_authorized", "READ", "STAFF_DIRECTORY_READ", "NONE", "Internal", _staff),
        ("organization_get_scope", "READ", "MANAGER_SCOPE_READ", "NONE", "Internal", _org_scope),
        ("news_search", "READ", "KNOWLEDGE_SEARCH", "NONE", "Public", _news),
        ("request_create_draft", "DRAFT", "REQUEST_DRAFT", "NONE", "Internal", _draft),
        ("request_submit_confirmed", "WRITE", "REQUEST_SUBMIT", "NONE", "Internal", _submit),
        ("notification_mark_read_confirmed", "WRITE", "NOTIFICATION_UPDATE", "NONE", "Internal", _mark_read),
    )
    for name, mode, purpose, step_up, classification, handler in definitions:
        registry.register(ToolDefinition(name, "1.0.0", mode, "SELF", purpose, (), step_up, classification, 3000, True, handler))
    return registry
