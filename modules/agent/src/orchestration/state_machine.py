from __future__ import annotations

from dataclasses import replace

from apps.api.src.schemas.common import RunStatus as ApiRunStatus
from modules.agent.contracts.run import ExecutionRoute, RunBudget, RunState, RunStatus


class StateMachine:
    """Deterministic agent-run state machine."""

    def __init__(self, session=None) -> None:
        self.session = session

    async def step(self, run_id: str, current_status: ApiRunStatus, target_status: ApiRunStatus | None = None) -> ApiRunStatus:
        """Advance a run by one permitted deterministic transition.

        """
        if self.session is None:
            raise RuntimeError("StateMachine requires an AsyncSession")
        import uuid
        from sqlalchemy import select
        from apps.api.src.db.models import AgentRun, RunEvent
        row = (await self.session.execute(select(AgentRun).where(AgentRun.id == uuid.UUID(run_id)).with_for_update())).scalar_one_or_none()
        if row is None or row.status != current_status.value:
            raise InvalidTransition("persisted run state changed")
        if target_status is None:
            raise InvalidTransition("target status is required")
        source = RunStatus[current_status.name]
        target = RunStatus[target_status.name]
        if target not in _ALLOWED.get(source, ()):
            raise InvalidTransition(f"cannot transition from {source.name} to {target.name}")
        row.status = target_status.value
        self.session.add(RunEvent(run_id=row.id, status=row.status, payload={}))
        await self.session.flush()
        return target_status


class InvalidTransition(ValueError):
    pass


_ALLOWED = {
    RunStatus.RECEIVED: {RunStatus.SENSITIVITY_CHECKED},
    RunStatus.SENSITIVITY_CHECKED: {RunStatus.AUTHORIZED, RunStatus.DENIED},
    RunStatus.AUTHORIZED: {RunStatus.ROUTED},
    RunStatus.ROUTED: {
        RunStatus.DETERMINISTIC,
        RunStatus.RETRIEVING,
        RunStatus.PLANNING,
    },
    RunStatus.DETERMINISTIC: {RunStatus.VALIDATING_OUTPUT},
    RunStatus.RETRIEVING: {RunStatus.EVALUATING_EVIDENCE, RunStatus.FAILED, RunStatus.CANCELLED},
    RunStatus.PLANNING: {RunStatus.EXECUTING_READ_TOOLS, RunStatus.FAILED, RunStatus.CANCELLED},
    RunStatus.EXECUTING_READ_TOOLS: {RunStatus.EVALUATING_EVIDENCE, RunStatus.FAILED, RunStatus.CANCELLED},
    RunStatus.EVALUATING_EVIDENCE: {
        RunStatus.RETRIEVING,
        RunStatus.GENERATING,
        RunStatus.INSUFFICIENT,
        RunStatus.CANCELLED,
    },
    RunStatus.GENERATING: {RunStatus.VALIDATING_OUTPUT, RunStatus.FAILED, RunStatus.CANCELLED},
    RunStatus.VALIDATING_OUTPUT: {
        RunStatus.COMPLETED,
        RunStatus.WAITING_CONFIRMATION,
        RunStatus.INSUFFICIENT,
        RunStatus.FAILED,
    },
    RunStatus.WAITING_CONFIRMATION: {RunStatus.EXECUTING_ACTION, RunStatus.CANCELLED},
    RunStatus.EXECUTING_ACTION: {RunStatus.COMPLETED, RunStatus.FAILED},
}


def transition(
    state: RunState,
    target: RunStatus,
    *,
    route: ExecutionRoute | None = None,
) -> RunState:
    if target not in _ALLOWED.get(state.status, ()):
        raise InvalidTransition(f"cannot transition from {state.status.name} to {target.name}")

    if target is RunStatus.ROUTED:
        if route is None:
            raise InvalidTransition("ROUTED requires an execution route")
        budgets = {
            ExecutionRoute.DETERMINISTIC: RunBudget.deterministic(),
            ExecutionRoute.SIMPLE_RAG: RunBudget.simple_rag(),
            ExecutionRoute.AGENTIC_READ: RunBudget.agentic_read(),
            ExecutionRoute.CONFIRMED_ACTION: RunBudget.confirmed_action(),
        }
        return replace(state, status=target, route=route, budget=budgets[route])

    if route is not None:
        raise InvalidTransition("route can only be assigned when entering ROUTED")

    return replace(state, status=target)
