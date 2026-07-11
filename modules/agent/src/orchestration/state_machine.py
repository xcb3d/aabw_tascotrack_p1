from dataclasses import replace

from modules.agent.contracts.run import ExecutionRoute, RunState, RunStatus


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


def transition(state: RunState, target: RunStatus, *, route=None):
    if target not in _ALLOWED.get(state.status, ()):
        raise InvalidTransition(f"cannot transition from {state.status.name} to {target.name}")

    if target is RunStatus.ROUTED:
        if route is not ExecutionRoute.DETERMINISTIC:
            raise InvalidTransition("ROUTED requires DETERMINISTIC route")
        return replace(state, status=target, route=route)

    if route is not None:
        raise InvalidTransition("route can only be assigned when entering ROUTED")

    return replace(state, status=target)
