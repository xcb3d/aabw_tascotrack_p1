import re

from modules.guardrails.contracts.verdicts import DlpResult, SensitivityVerdict

_PATTERNS = (
    ("PRIVATE_KEY", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("BEARER_TOKEN", re.compile(r"\bBearer\s+[-._~+/=A-Za-z0-9]+", re.IGNORECASE)),
    ("SECRET_ASSIGNMENT", re.compile(r"\b(?:api[_-]?key|password|secret)\b\s*[:=]\s*[^\s,;]+", re.IGNORECASE)),
    ("OTP", re.compile(r"\b(?:otp(?:TransactionId)?|one[- ]time password)\b(?:\s+(?:value|code|id))?\s*(?:[:=]|is)?\s*[A-Za-z0-9-]+", re.IGNORECASE)),
    ("PAYROLL", re.compile(r"\b(?:salary|payroll|wage|lương|luong|bảng lương|bang luong)\b[^\n\r]*\d[\d.,]*(?:\s*(?:vnd|vnđ|usd|đ|dollars?))?", re.IGNORECASE)),
)


def _codes(text: str) -> tuple[str, ...]:
    found: list[tuple[int, int, str]] = []
    for order, (code, pattern) in enumerate(_PATTERNS):
        for match in pattern.finditer(text):
            found.append((match.start(), order, code))
    seen = set()
    codes = []
    for _, _, code in sorted(found):
        if code not in seen:
            seen.add(code)
            codes.append(code)
    return tuple(codes)


def sensitivity_gate(text: str) -> SensitivityVerdict:
    codes = _codes(text)
    return SensitivityVerdict(egress_allowed=not codes, codes=codes)


def redact(text: str) -> DlpResult:
    codes = _codes(text)
    sanitized = text
    for code, pattern in _PATTERNS:
        sanitized = pattern.sub(f"[REDACTED:{code}]", sanitized)
    return DlpResult(sanitized_text=sanitized, codes=codes)
