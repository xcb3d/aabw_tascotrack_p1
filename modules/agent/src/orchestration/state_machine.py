from __future__ import annotations

from apps.api.src.schemas.common import RunStatus


class StateMachine:
    """Deterministic agent-run state machine."""

    async def step(self, run_id: str, current_status: RunStatus) -> RunStatus:
        """Advance a run by one permitted deterministic transition.

        # TODO: persist transition atomically and dispatch worker commands.
        """
        raise NotImplementedError("StateMachine.step")
