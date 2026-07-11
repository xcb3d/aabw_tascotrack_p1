from __future__ import annotations

from fastapi import APIRouter, Depends

from apps.api.src.dependencies import get_request_id
from apps.api.src.schemas.evaluation import CreateEvaluationRunRequest, PublicEvaluationRequest
from apps.api.src.schemas.envelope import GenericEnvelope

router = APIRouter(tags=["Evaluation"])


@router.post("/mytasco/v1/aiwsp/evaluation/public", operation_id="runPublicEvaluation")
async def run_public_evaluation(
    body: PublicEvaluationRequest | None = None,
    request_id: str = Depends(get_request_id),
) -> GenericEnvelope:
    """Run the provided public evaluation set."""
    # TODO: execute evaluation cases against current model config.
    raise NotImplementedError("runPublicEvaluation")


@router.post("/mytasco/v1/aiwsp/evaluations/runs", operation_id="createEvaluationRun")
async def create_evaluation_run(
    body: CreateEvaluationRunRequest,
    request_id: str = Depends(get_request_id),
) -> GenericEnvelope:
    """Start a versioned quality/security evaluation."""
    # TODO: persist evaluation run, enqueue worker job.
    raise NotImplementedError("createEvaluationRun")