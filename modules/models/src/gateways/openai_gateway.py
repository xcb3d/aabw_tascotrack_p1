from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class ModelGatewayError(RuntimeError):
    pass


DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


@dataclass(frozen=True)
class ModelRequest:
    instructions: str
    input: list[dict[str, Any]]
    schema_name: str
    schema: dict[str, Any]
    safety_identifier: str
    model: str | None = None
    reasoning_effort: str = "medium"


@dataclass(frozen=True)
class ModelResponse:
    output: dict[str, Any]
    model: str
    response_id: str
    usage: dict[str, Any]


class ModelGateway(Protocol):
    async def respond(self, request: ModelRequest) -> ModelResponse: ...


class OpenAIResponsesGateway:
    """The sole hosted-model boundary; accepts only structured, non-hosted-tool calls."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str,
        base_url: str = DEFAULT_OPENAI_BASE_URL,
        timeout_seconds: float = 45.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI API key is required")
        self._api_key = api_key
        self._model = model
        self._url = f"{(base_url or DEFAULT_OPENAI_BASE_URL).rstrip('/')}/responses"
        self._timeout = timeout_seconds
        self._client = client

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(min=0.5, max=2),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def create_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        vetted = dict(payload)
        vetted["store"] = False
        vetted.pop("tools", None)
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        if self._client is not None:
            response = await self._client.post(self._url, headers=headers, json=vetted, timeout=self._timeout)
        else:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(self._url, headers=headers, json=vetted)
        if response.status_code >= 400:
            try:
                error = response.json().get("error") or {}
                metadata = ":".join(str(error.get(key) or "") for key in ("type", "code", "param")).strip(":")
            except (ValueError, AttributeError):
                metadata = ""
            suffix = f" ({metadata})" if metadata else ""
            raise ModelGatewayError(f"OpenAI Responses API returned HTTP {response.status_code}{suffix}")
        value = response.json()
        if not isinstance(value, dict):
            raise ModelGatewayError("OpenAI response must be an object")
        return value

    async def respond(self, request: ModelRequest) -> ModelResponse:
        payload = {
            "model": request.model or self._model,
            "instructions": request.instructions,
            "input": request.input,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": request.schema_name,
                    "strict": True,
                    "schema": request.schema,
                }
            },
            "safety_identifier": request.safety_identifier,
            "store": False,
        }
        selected_model = str(payload["model"])
        if selected_model.startswith(("gpt-5", "o1", "o3", "o4")):
            payload["reasoning"] = {"effort": request.reasoning_effort}
        raw = await self.create_response(payload)
        text = _output_text(raw)
        try:
            output = json.loads(text)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ModelGatewayError("model returned invalid structured JSON") from exc
        if not isinstance(output, dict):
            raise ModelGatewayError("structured model output must be an object")
        return ModelResponse(
            output=output,
            model=str(raw.get("model") or payload["model"]),
            response_id=str(raw.get("id") or ""),
            usage=dict(raw.get("usage") or {}),
        )


def _output_text(raw: dict[str, Any]) -> str:
    if isinstance(raw.get("output_text"), str):
        return raw["output_text"]
    for item in raw.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                return content["text"]
    raise ModelGatewayError("model response contained no output text")


class FakeResponsesGateway:
    """Deterministic CI gateway that emits grounded claims from supplied evidence."""

    async def respond(self, request: ModelRequest) -> ModelResponse:
        evidence: list[dict[str, Any]] = []
        for item in request.input:
            content = item.get("content") if isinstance(item, dict) else None
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and isinstance(block.get("text"), str):
                        try:
                            parsed = json.loads(block["text"])
                            if isinstance(parsed, list):
                                evidence.extend(row for row in parsed if isinstance(row, dict))
                        except json.JSONDecodeError:
                            pass
        if evidence:
            ids = [str(row.get("evidence_id")) for row in evidence if row.get("evidence_id")]
            answer = " ".join(str(row.get("content", "")) for row in evidence[:2]).strip()
            output = {
                "status": "ANSWER",
                "answer": answer,
                "claims": [{"claim_id": "c1", "text": answer, "evidence_ids": ids}],
                "confidence": "MEDIUM",
            }
        else:
            output = {"status": "INSUFFICIENT_EVIDENCE", "answer": "", "claims": [], "confidence": "LOW"}
        digest = hashlib.sha256(_stable_json(output).encode()).hexdigest()[:24]
        return ModelResponse(output, "fake-responses-v1", f"fake_{digest}", {"input_tokens": 0, "output_tokens": 0})


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
