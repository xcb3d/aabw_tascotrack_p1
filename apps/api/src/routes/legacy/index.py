from __future__ import annotations

from fastapi import APIRouter, Depends

from apps.api.src.config import get_settings
from apps.api.src.dependencies import get_request_id
from apps.api.src.schemas.envelope import GenericEnvelope

router = APIRouter(tags=["Legacy", "Documents"])


@router.post("/mytasco/v1/aiwsp/index/rebuild", operation_id="rebuildIndex")
async def rebuild_index(
    request_id: str = Depends(get_request_id),
) -> GenericEnvelope:
    """Rebuild the prototype vector index (demo-only endpoint)."""
    settings = get_settings()
    if settings.ENV == "production":
        raise NotImplementedError("rebuildIndex is disabled in production")

    # TODO: enqueue prototype index rebuild; replace with governed ingestion flow.
    raise NotImplementedError("rebuildIndex")
