import json
import re

from modules.guardrails.contracts.verdicts import DlpResult, SensitivityVerdict

def _json_key_pattern(key: str) -> str:
    return "".join(rf"(?:{re.escape(char)}|\\u{ord(char):04x})" for char in key)


_PAYROLL_JSON_KEY = "|".join(
    _json_key_pattern(key) for key in ("grossSalary", "netSalary", "gross_salary", "net_salary", "salary", "payroll")
)


_PATTERNS = (
    ("PRIVATE_KEY", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----")),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*\Z")),
    ("BEARER_TOKEN", re.compile(r"\bBearer\s+[-._~+/=A-Za-z0-9]+", re.IGNORECASE)),
    ("AUTH_TOKEN", re.compile(r"(([\"'])(?:api[_-]?key|password|secret)\2\s*:\s*([\"']))(?:\\.|(?!\3)[^\\\r\n])*(\3)", re.IGNORECASE)),
    ("AUTH_TOKEN", re.compile(r"((?:\"(?:api[_-]?key|password|secret)\"|'(?:api[_-]?key|password|secret)')\s*:\s*)(?:\"(?:\\.|[^\"\\\r\n])*|'(?:\\.|[^'\\\r\n])*)(?=\r?\n|\Z)", re.IGNORECASE)),
    ("AUTH_TOKEN", re.compile(r"(\b(?:api[_-]?key|password|secret)\b\s*[:=]\s*)[^\r\n,;]+", re.IGNORECASE)),
    ("OTP", re.compile(r"(([\"'])otpTransactionId\2\s*:\s*([\"']))(?:\\.|(?!\3)[^\\\r\n])*(\3)", re.IGNORECASE)),
    ("OTP", re.compile(r"((?:\"otpTransactionId\"|'otpTransactionId')\s*:\s*)(?:\"(?:\\.|[^\"\\\r\n])*|'(?:\\.|[^'\\\r\n])*)(?=\r?\n|\Z)", re.IGNORECASE)),
    ("OTP", re.compile(r"\b(?:otp(?:TransactionId)?|one[- ]time password)\b(?:\s+(?:value|code|id))?\s*(?:[:=]|is)?\s*[A-Za-z0-9-]+", re.IGNORECASE)),
    ("PAYROLL", re.compile(rf"[\"'](?:{_PAYROLL_JSON_KEY})[\"']\s*:\s*[\"']?\d[\d.,]*", re.IGNORECASE)),
    ("PAYROLL", re.compile(r"\b(?:salary|payroll|wage|lương|luong|bảng lương|bang luong)\b[^\n\r]*\d[\d.,]*(?:\s*(?:vnd|vnđ|usd|đ|dollars?))?", re.IGNORECASE)),
)

_VALUE_ONLY_CODES = {"AUTH_TOKEN", "OTP"}
_ASSIGNMENT_KEYS = {"apikey", "password", "secret"}
_OTP_KEYS = {"otptransactionid"}


def _normalized_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.casefold())


def _json_key_code(key: str) -> str | None:
    normalized = _normalized_key(key)
    if normalized in _ASSIGNMENT_KEYS:
        return "AUTH_TOKEN"
    if normalized in _OTP_KEYS:
        return "OTP"
    if "salary" in normalized or "payroll" in normalized:
        return "PAYROLL"
    return None


def _json_codes(value) -> tuple[str, ...]:
    codes = []
    seen = set()

    def add(code: str) -> None:
        if code not in seen:
            seen.add(code)
            codes.append(code)

    def walk(item, depth: int = 0) -> None:
        if isinstance(item, dict):
            for key, value in item.items():
                code = _json_key_code(key)
                if code:
                    add(code)
                walk(value, depth)
        elif isinstance(item, list):
            for value in item:
                walk(value, depth)
        elif isinstance(item, str) and depth < 3 and item[:1] in "[{":
            try:
                walk(json.loads(item), depth + 1)
            except json.JSONDecodeError:
                pass

    walk(value)
    return tuple(codes)


def _decoded_json_codes(text: str) -> tuple[str, ...]:
    try:
        return _json_codes(json.loads(text))
    except json.JSONDecodeError:
        return ()


def _replacement(code: str):
    redacted = f"[REDACTED:{code}]"

    def replace(match: re.Match[str]) -> str:
        if code in _VALUE_ONLY_CODES and match.lastindex:
            suffix = match.group(match.lastindex) if match.lastindex > 1 else ""
            return f"{match.group(1)}{redacted}{suffix}"
        return redacted

    return replace


def _codes(text: str) -> tuple[str, ...]:
    json_codes = _decoded_json_codes(text)
    if json_codes:
        return json_codes

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
    if codes and _decoded_json_codes(text):
        markers = ",".join(f"[REDACTED:{code}]" for code in codes)
        return DlpResult(sanitized_text=markers, codes=codes)

    sanitized = text
    for code, pattern in _PATTERNS:
        sanitized = pattern.sub(_replacement(code), sanitized)
    return DlpResult(sanitized_text=sanitized, codes=codes)
