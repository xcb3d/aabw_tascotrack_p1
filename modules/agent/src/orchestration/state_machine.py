from __future__ import annotations

from dataclasses import replace

from apps.api.src.schemas.common import RunStatus as ApiRunStatus
from modules.agent.contracts.run import ExecutionRoute, RunBudget, RunState, RunStatus


class StateMachine:
    """Deterministic agent-run state machine."""

    async def step(self, run_id: str, current_status: ApiRunStatus) -> ApiRunStatus:
        """Advance a run by one permitted deterministic transition.

        # TODO: persist transition atomically and dispatch worker commands.
        """
        raise NotImplementedError("StateMachine.step")


class InvalidTransition(ValueError):
    pass


_ALLOWED = {
    RunStatus.RECEIVED: {RunStatus.SENSITIVITY_CHECKED},
    RunStatus.SENSITIVITY_CHECKED: {RunStatus.AUTHORIZED, RunStatus.DENIED},
    RunStatus.AUTHORIZED: {RunStatus.ROUTED},
    RunStatus.ROUTED: {RunStatus.DETERMINISTIC},
    RunStatus.DETERMINISTIC: {RunStatus.VALIDATING_OUTPUT},
    RunStatus.VALIDATING_OUTPUT: {RunStatus.COMPLETED},
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
        if route is not ExecutionRoute.DETERMINISTIC:
            raise InvalidTransition("ROUTED requires DETERMINISTIC route")
        return replace(state, status=target, route=route, budget=RunBudget.deterministic())

    if route is not None:
        raise InvalidTransition("route can only be assigned when entering ROUTED")

    return replace(state, status=target)
