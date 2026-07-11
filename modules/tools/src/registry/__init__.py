from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable


ToolHandler = Callable[[dict[str, Any], Any], Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    version: str
    mode: str
    resource_scope: str
    required_purpose: str
    required_permissions: tuple[str, ...]
    required_step_up: str
    data_classification: str
    timeout_ms: int
    idempotent: bool
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        if definition.name in self._tools:
            raise ValueError(f"tool already registered: {definition.name}")
        if definition.mode not in {"READ", "DRAFT", "WRITE"}:
            raise ValueError("invalid tool mode")
        self._tools[definition.name] = definition

    def get(self, tool_name: str) -> ToolDefinition:
        try:
            return self._tools[tool_name]
        except KeyError as exc:
            raise KeyError(f"unknown or disabled tool: {tool_name}") from exc

    def snapshot(self, names: tuple[str, ...]) -> tuple[ToolDefinition, ...]:
        return tuple(self.get(name) for name in names)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))
