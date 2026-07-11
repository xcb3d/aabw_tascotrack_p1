from __future__ import annotations

from typing import Any


class ToolRegistry:
    """Registry of typed, policy-gated tool adapters."""

    def get(self, tool_name: str) -> Any:
        """Return a registered tool adapter.

        # TODO: resolve registered adapter and enforce tool policy metadata.
        """
        raise NotImplementedError("ToolRegistry.get")
