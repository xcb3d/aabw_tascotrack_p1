from __future__ import annotations

from fastapi import APIRouter, Depends

from apps.api.src.config import get_settings
from apps.api.src.dependencies import get_request_id
from apps.api.src.schemas.envelope import GenericEnvelope

router = APIRouter(tags=["Legacy"])


@router.get("/mytasco/v1/aiwsp/users", operation_id="listDemoUsers")
async def list_demo_users(
    request_id: str = Depends(get_request_id),
) -> GenericEnvelope:
    """List synthetic demo users.

    This endpoint must be disabled in production environments.
    """
    settings = get_settings()
    if settings.ENV == "production":
        raise NotImplementedError("listDemoUsers is disabled in production")

    # TODO: return synthetic user inventory from seed data.
    raise NotImplementedError("listDemoUsers")