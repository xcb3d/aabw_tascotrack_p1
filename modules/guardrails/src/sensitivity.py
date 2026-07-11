from __future__ import annotations

from apps.api.src.schemas.common import Classification


def classify_sensitivity(value: str) -> Classification:
    """Classify content sensitivity before retrieval, egress, or persistence.

    # TODO: implement deterministic sensitivity rules and review workflow.
    """
    raise NotImplementedError("classify_sensitivity")
