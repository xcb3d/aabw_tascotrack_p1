import re

from modules.guardrails.contracts.verdicts import DlpResult, SensitivityVerdict

_PATTERNS = (
    ("PRIVATE_KEY", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----")),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*\Z")),
    ("BEARER_TOKEN", re.compile(r"\bBearer\s+[-._~+/=A-Za-z0-9]+", re.IGNORECASE)),
    ("SECRET_ASSIGNMENT", re.compile(r"(([\"'])(?:api[_-]?key|password|secret)\2\s*:\s*([\"']))(?:\\.|(?!\3)[^\\\r\n])*(\3)", re.IGNORECASE)),
    ("SECRET_ASSIGNMENT", re.compile(r"((?:\"(?:api[_-]?key|password|secret)\"|'(?:api[_-]?key|password|secret)')\s*:\s*)(?:\"(?:\\.|[^\"\\\r\n])*|'(?:\\.|[^'\\\r\n])*)(?=\r?\n|\Z)", re.IGNORECASE)),
    ("SECRET_ASSIGNMENT", re.compile(r"(\b(?:api[_-]?key|password|secret)\b\s*[:=]\s*)[^\r\n,;]+", re.IGNORECASE)),
    ("OTP", re.compile(r"(([\"'])otpTransactionId\2\s*:\s*([\"']))(?:\\.|(?!\3)[^\\\r\n])*(\3)", re.IGNORECASE)),
    ("OTP", re.compile(r"((?:\"otpTransactionId\"|'otpTransactionId')\s*:\s*)(?:\"(?:\\.|[^\"\\\r\n])*|'(?:\\.|[^'\\\r\n])*)(?=\r?\n|\Z)", re.IGNORECASE)),
    ("OTP", re.compile(r"\b(?:otp(?:TransactionId)?|one[- ]time password)\b(?:\s+(?:value|code|id))?\s*(?:[:=]|is)?\s*[A-Za-z0-9-]+", re.IGNORECASE)),
    ("PAYROLL", re.compile(r"\b(?:salary|payroll|wage|lương|luong|bảng lương|bang luong)\b[^\n\r]*\d[\d.,]*(?:\s*(?:vnd|vnđ|usd|đ|dollars?))?", re.IGNORECASE)),
)

_VALUE_ONLY_CODES = {"SECRET_ASSIGNMENT", "OTP"}


def _replacement(code: str):
    redacted = f"[REDACTED:{code}]"

    def replace(match: re.Match[str]) -> str:
        if code in _VALUE_ONLY_CODES and match.lastindex:
            suffix = match.group(match.lastindex) if match.lastindex > 1 else ""
            return f"{match.group(1)}{redacted}{suffix}"
        return redacted

    return replace


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
        sanitized = pattern.sub(_replacement(code), sanitized)
    return DlpResult(sanitized_text=sanitized, codes=codes)
