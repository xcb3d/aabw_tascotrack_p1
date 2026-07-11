from __future__ import annotations

from typing import Any

from modules.guardrails.src.dlp.screening import redact, sensitivity_gate
import re


def scan_input(value: str) -> dict[str, Any]:
    """Scan input for sensitive data and prompt-injection indicators.

    """
    verdict = sensitivity_gate(value)
    result = redact(value)
    injection_terms = ("ignore previous instructions", "system prompt", "developer message", "bỏ qua hướng dẫn")
    injection = any(term in value.casefold() for term in injection_terms)
    pii_types = []
    if re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", value, re.IGNORECASE):
        pii_types.append("EMAIL")
    if re.search(r"(?<!\d)(?:\+84|0)\d{9,10}(?!\d)", value):
        pii_types.append("PHONE")
    return {"allowed": verdict.egress_allowed and not injection, "codes": list(verdict.codes) + (["PROMPT_INJECTION"] if injection else []), "piiTypes": pii_types, "sanitized": result.sanitized_text}
