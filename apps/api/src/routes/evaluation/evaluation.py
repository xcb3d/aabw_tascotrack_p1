from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.db.models import EvaluationRun, Job
from apps.api.src.dependencies import get_current_subject, get_db, get_request_id
from apps.api.src.schemas.evaluation import CreateEvaluationRunRequest, PublicEvaluationRequest
from apps.api.src.schemas.envelope import GenericEnvelope
from modules.governance.src.evaluation.public_harness import evaluate_public_cases
from modules.governance.src.evaluation.xlsm_dataset import load_public_evaluation_dataset
from modules.identity.src.subject import SubjectContext

router = APIRouter(tags=["Evaluation"])
DATASET = Path("package/ai_workspace_dataset_vietnamese_participants.xlsm")


@router.post("/mytasco/v1/aiwsp/evaluation/public", operation_id="runPublicEvaluation")
async def run_public_evaluation(body: PublicEvaluationRequest | None = None, request_id: str = Depends(get_request_id), subject: SubjectContext = Depends(get_current_subject)) -> GenericEnvelope:
    if not subject.is_admin:
        raise HTTPException(status_code=403, detail="Administrator role required")
    results = evaluate_public_cases(load_public_evaluation_dataset(DATASET))
    if body and body.limit:
        results = results[:body.limit]
    passed = sum(item.actual_permission == item.expected_permission for item in results)
    return GenericEnvelope(body={"datasetId": DATASET.name, "total": len(results), "passed": passed, "passRate": passed / len(results) if results else 0, "results": [asdict(item) for item in results]}, requestId=request_id)


@router.post("/mytasco/v1/aiwsp/evaluations/runs", operation_id="createEvaluationRun", status_code=202)
async def create_evaluation_run(body: CreateEvaluationRunRequest, request_id: str = Depends(get_request_id), subject: SubjectContext = Depends(get_current_subject), db: AsyncSession = Depends(get_db)) -> GenericEnvelope:
    if not subject.is_admin:
        raise HTTPException(status_code=403, detail="Administrator role required")
    row = EvaluationRun(tenant_id=subject.tenant_id, owner_id=subject.subject_id, dataset_id=body.datasetId, candidate_config_id=body.candidateConfigId, baseline_config_id=body.baselineConfigId)
    db.add(row)
    await db.flush()
    db.add(Job(queue="evaluation", job_type="evaluation", payload={"evaluationRunId": str(row.id)}))
    await db.commit()
    return GenericEnvelope(body={"evaluationRunId": str(row.id), "status": row.status}, requestId=request_id)
