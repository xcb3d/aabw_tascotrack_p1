from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

# This is the only source file permitted to reference the OpenAI endpoint.
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


class OpenAIResponsesGateway:
    """Internal-only OpenAI Responses API gateway."""

    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None) -> None:
        self._api_key = api_key
        self._client = client

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def create_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a vetted Responses API request.

        # TODO: enforce policy egress hooks, bounded timeouts, store=false, and structured outputs.
        """
        raise NotImplementedError("OpenAIResponsesGateway.create_response")
