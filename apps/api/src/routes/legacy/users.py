from __future__ import annotations

from fastapi import APIRouter, Depends

from apps.api.src.config import get_settings
from apps.api.src.dependencies import get_current_subject, get_request_id
from apps.api.src.schemas.envelope import GenericEnvelope
from modules.identity.src.subject import SubjectContext

router = APIRouter(tags=["Legacy"])


@router.get("/mytasco/v1/aiwsp/users", operation_id="listDemoUsers")
async def list_demo_users(
    request_id: str = Depends(get_request_id),
    subject: SubjectContext = Depends(get_current_subject),
) -> GenericEnvelope:
    """List synthetic demo users.

    This endpoint must be disabled in production environments.
    """
    settings = get_settings()
    if settings.ENV == "production":
        raise NotImplementedError("listDemoUsers is disabled in production")

    if not subject.is_admin:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Administrator role required")
    users = [
        {"userId": "U001", "role": "Employee", "department": "Human Resources", "tenantId": subject.tenant_id},
        {"userId": "U031", "role": "Executive", "department": "Executive Office", "tenantId": subject.tenant_id},
    ]
    return GenericEnvelope(body={"result": users, "synthetic": True}, requestId=request_id)
