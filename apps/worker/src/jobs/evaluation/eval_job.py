from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.db.models import EvaluationRun
from modules.governance.src.audit import append_audit
from modules.governance.src.evaluation.public_harness import evaluate_public_cases
from modules.governance.src.evaluation.xlsm_dataset import load_public_evaluation_dataset


async def evaluate_run_job(session: AsyncSession, evaluation_run_id: str) -> None:
    row = await session.get(EvaluationRun, uuid.UUID(evaluation_run_id))
    if row is None:
        raise LookupError("evaluation run not found")
    await append_audit(session, "evaluation.started", {"evaluationRunId": evaluation_run_id}, tenant_id=row.tenant_id, actor_id=row.owner_id)
    results = evaluate_public_cases(load_public_evaluation_dataset(Path("package/ai_workspace_dataset_vietnamese_participants.xlsm")))
    passed = sum(item.actual_permission == item.expected_permission for item in results)
    row.metrics = {"total": len(results), "passed": passed, "passRate": passed / len(results)}
    row.status = "COMPLETED"
    await append_audit(session, "evaluation.completed", {"evaluationRunId": evaluation_run_id, "passed": passed, "total": len(results)}, tenant_id=row.tenant_id, actor_id=row.owner_id)
    await session.commit()
