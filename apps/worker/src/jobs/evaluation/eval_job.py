from __future__ import annotations

from modules.governance.src.audit import append_audit


async def evaluate_run_job(evaluation_run_id: str) -> None:
    """Run a versioned quality and security evaluation.

    # TODO: load dataset/config snapshots, evaluate candidate, persist metrics/artifacts.
    """
    await append_audit("evaluation.started", {"evaluationRunId": evaluation_run_id})
    raise NotImplementedError("evaluate_run_job")
