from __future__ import annotations

from apps.api.src.schemas.common import Classification
from modules.guardrails.src.dlp.screening import sensitivity_gate


def classify_sensitivity(value: str) -> Classification:
    """Classify content sensitivity before retrieval, egress, or persistence.

    """
    codes = set(sensitivity_gate(value).codes)
    if codes.intersection({"PRIVATE_KEY", "BEARER_TOKEN", "AUTH_TOKEN", "OTP", "COOKIE"}):
        return Classification.RESTRICTED
    if "PAYROLL" in codes:
        return Classification.RESTRICTED
    return Classification.INTERNAL
