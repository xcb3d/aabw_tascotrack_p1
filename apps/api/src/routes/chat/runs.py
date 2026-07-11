from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from apps.api.src.dependencies import get_request_id, require_idempotency_key
from apps.api.src.schemas.chat import AgentRunRequest, AgentRunEnvelope

router = APIRouter(tags=["Chat"])


@router.post("/mytasco/v1/aiwsp/chat/runs", operation_id="createAgentRun")
async def create_agent_run(
    body: AgentRunRequest,
    idempotency_key: str = Depends(require_idempotency_key),
    request_id: str = Depends(get_request_id),
) -> AgentRunEnvelope:
    """Start a secure deterministic, RAG, agentic-read, or action-preview run."""
    # TODO: persist run, enqueue worker job, return initial state.
    raise NotImplementedError("createAgentRun")


@router.get("/mytasco/v1/aiwsp/chat/runs/{run_id}", operation_id="getAgentRun")
async def get_agent_run(
    run_id: str,
    request_id: str = Depends(get_request_id),
) -> AgentRunEnvelope:
    """Get a run owned by the current subject."""
    # TODO: query persisted run state.
    raise NotImplementedError("getAgentRun")


@router.get("/mytasco/v1/aiwsp/chat/runs/{run_id}/events", operation_id="streamAgentRunEvents")
async def stream_agent_run_events(run_id: str) -> StreamingResponse:
    """Stream high-level run status events via SSE.

    Streams status only. The final validated answer is emitted exactly once after validation.
    """
    # TODO: connect to run event stream and yield ServerSentEvents.
    async def event_generator():
        yield "event: error\ndata: {}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/mytasco/v1/aiwsp/chat/runs/{run_id}/cancel", operation_id="cancelAgentRun")
async def cancel_agent_run(
    run_id: str,
    request_id: str = Depends(get_request_id),
) -> AgentRunEnvelope:
    """Cancel an active run."""
    # TODO: signal cancellation on the run state machine.
    raise NotImplementedError("cancelAgentRun")