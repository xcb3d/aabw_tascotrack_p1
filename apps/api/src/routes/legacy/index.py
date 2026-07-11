from __future__ import annotations

from fastapi import APIRouter, Depends

from apps.api.src.config import get_settings
from apps.api.src.db.models import Job
from apps.api.src.dependencies import get_current_subject, get_db, get_request_id
from apps.api.src.schemas.envelope import GenericEnvelope
from modules.identity.src.subject import SubjectContext
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["Legacy", "Documents"])


@router.post("/mytasco/v1/aiwsp/index/rebuild", operation_id="rebuildIndex")
async def rebuild_index(
    request_id: str = Depends(get_request_id),
    subject: SubjectContext = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
) -> GenericEnvelope:
    """Rebuild the prototype vector index (demo-only endpoint)."""
    settings = get_settings()
    if settings.ENV == "production":
        raise NotImplementedError("rebuildIndex is disabled in production")

    if not subject.is_admin:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Administrator role required")
    job = Job(queue="ingestion", job_type="rebuild_index", payload={"tenantId": subject.tenant_id})
    db.add(job)
    await db.commit()
    return GenericEnvelope(body={"jobId": str(job.id), "status": job.status}, requestId=request_id)
