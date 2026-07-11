from __future__ import annotations

import asyncio
import socket
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from apps.api.src.config import get_settings
from apps.api.src.db.models import Job
from apps.api.src.db.session import dispose_engine, get_session_factory
from apps.worker.src.jobs.agent_runs.run_job import run_agent_job
from apps.worker.src.jobs.ingestion.ingest_job import ingest_document_job
from apps.api.src.db.models import DocumentVersion, EvaluationRun
from modules.governance.src.evaluation.public_harness import evaluate_public_cases
from modules.governance.src.evaluation.xlsm_dataset import load_public_evaluation_dataset
from pathlib import Path


async def process_one() -> bool:
    settings = get_settings()
    async with get_session_factory()() as session:
        await session.execute(update(Job).where(Job.status == "RUNNING", Job.locked_at < datetime.now(timezone.utc) - timedelta(minutes=5)).values(status="PENDING", locked_by=None, locked_at=None))
        await session.commit()
        job = (await session.execute(select(Job).where(Job.status == "PENDING", Job.available_at <= datetime.now(timezone.utc)).order_by(Job.created_at).with_for_update(skip_locked=True).limit(1))).scalar_one_or_none()
        if job is None:
            return False
        job.status, job.locked_by, job.locked_at = "RUNNING", socket.gethostname(), datetime.now(timezone.utc)
        job.attempts += 1
        await session.commit()
        try:
            if job.job_type == "agent_run":
                await run_agent_job(session, job.payload["runId"], job.payload["subject"], settings)
            elif job.job_type == "ingest_document":
                await ingest_document_job(session, job.payload["documentId"], job.payload["versionId"], settings)
            elif job.job_type == "rebuild_index":
                versions = (await session.execute(select(DocumentVersion).where(DocumentVersion.status.in_(("ready", "active"))))).scalars().all()
                for version in versions:
                    version.status = "processing"
                    await ingest_document_job(session, str(version.document_id), str(version.id), settings)
            elif job.job_type == "evaluation":
                row = await session.get(EvaluationRun, job.payload["evaluationRunId"])
                if row is None:
                    raise LookupError("evaluation run not found")
                results = evaluate_public_cases(load_public_evaluation_dataset(Path("package/ai_workspace_dataset_vietnamese_participants.xlsm")))
                passed = sum(item.actual_permission == item.expected_permission for item in results)
                row.metrics = {"total": len(results), "passed": passed, "passRate": passed / len(results)}
                row.status = "COMPLETED"
            else:
                raise ValueError("unknown job type")
            job.status = "COMPLETED"
        except Exception as exc:
            await session.rollback()
            job = await session.get(Job, job.id)
            if job is None:
                raise
            job.error_code = type(exc).__name__
            if job.attempts < job.max_attempts:
                job.status, job.available_at = "PENDING", datetime.now(timezone.utc) + timedelta(seconds=2 ** job.attempts)
            else:
                job.status = "DEAD"
        await session.commit()
        return True


async def run_forever() -> None:
    while True:
        if not await process_one():
            await asyncio.sleep(0.5)


if __name__ == "__main__":
    async def main() -> None:
        try:
            await run_forever()
        finally:
            await dispose_engine()

    asyncio.run(main())
