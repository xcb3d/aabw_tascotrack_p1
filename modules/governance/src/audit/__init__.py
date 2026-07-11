from __future__ import annotations

from typing import Any


async def append_audit(event_type: str, payload: dict[str, Any]) -> None:
    """Append a content-free governance audit event.

    # TODO: persist signed/immutable audit event with request and trace context.
    """
    raise NotImplementedError("append_audit")
