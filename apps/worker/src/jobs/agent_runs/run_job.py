from __future__ import annotations

from apps.api.src.schemas.common import RunStatus
from modules.agent.src.orchestration.state_machine import StateMachine


async def run_agent_job(run_id: str) -> None:
    """Advance an accepted agent run in the worker.

    # TODO: load run context, call guardrails/policy/retrieval/state machine, append audit events.
    """
    state_machine = StateMachine()
    await state_machine.step(run_id, RunStatus.RECEIVED)
    raise NotImplementedError("run_agent_job")
