import json
import re

from modules.guardrails.contracts.verdicts import DlpResult, SensitivityVerdict

def _json_key_pattern(key: str) -> str:
    def char_pattern(char: str) -> str:
        escaped = {rf"\\u{ord(variant):04x}" for variant in {char, char.lower(), char.upper()}}
        return rf"(?:{re.escape(char)}|{'|'.join(sorted(escaped))})"

    return "".join(char_pattern(char) for char in key)


_PAYROLL_JSON_KEY = "|".join(
    _json_key_pattern(key) for key in ("grossSalary", "netSalary", "gross_salary", "net_salary", "salary", "payroll")
)
_AUTH_JSON_KEY = "|".join(_json_key_pattern(key) for key in ("apiKey", "api_key", "password", "secret"))
_OTP_JSON_KEY = _json_key_pattern("otpTransactionId")
_COOKIE_JSON_KEY = "|".join(_json_key_pattern(key) for key in ("cookie", "cookies", "session", "sessionId", "session_id"))
_JSON_MAX_DEPTH = 3
_MALFORMED_STRUCTURED_DATA = "MALFORMED_STRUCTURED_DATA"
_STRUCTURED_DATA_LIMIT = "STRUCTURED_DATA_LIMIT"


_PATTERNS = (
    ("PRIVATE_KEY", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----")),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*\Z")),
    ("BEARER_TOKEN", re.compile(r"\bBearer\s+[-._~+/=A-Za-z0-9]+", re.IGNORECASE)),
    ("AUTH_TOKEN", re.compile(r"(\bAuthorization\s*:\s*)Basic\s+\S+", re.IGNORECASE)),
    ("AUTH_TOKEN", re.compile(rf"(([\"'])(?:{_AUTH_JSON_KEY})\2\s*:\s*([\"']))(?:\\.|(?!\3)[^\\\r\n])*(\3)", re.IGNORECASE)),
    ("AUTH_TOKEN", re.compile(rf"((?:\"(?:{_AUTH_JSON_KEY})\"|'(?:{_AUTH_JSON_KEY})')\s*:\s*)(?:\"(?:\\.|[^\"\\\r\n])*|'(?:\\.|[^'\\\r\n])*)(?=\r?\n|\Z)", re.IGNORECASE)),
    ("AUTH_TOKEN", re.compile(r"(\b(?:api[_-]?key|password|secret)\b\s*[:=]\s*)[^\r\n,;]+", re.IGNORECASE)),
    ("OTP", re.compile(rf"(([\"']){_OTP_JSON_KEY}\2\s*:\s*([\"']))(?:\\.|(?!\3)[^\\\r\n])*(\3)", re.IGNORECASE)),
    ("OTP", re.compile(rf"((?:\"{_OTP_JSON_KEY}\"|'{_OTP_JSON_KEY}')\s*:\s*)(?:\"(?:\\.|[^\"\\\r\n])*|'(?:\\.|[^'\\\r\n])*)(?=\r?\n|\Z)", re.IGNORECASE)),
    ("OTP", re.compile(r"\b(?:otp(?:TransactionId)?|one[- ]time password)\b(?:\s+(?:value|code|id))?\s*(?:[:=]|is)?\s*[A-Za-z0-9-]+", re.IGNORECASE)),
    ("COOKIE", re.compile(r"((?:^|\r?\n)\s*(?:Set-)?Cookie\s*:\s*)[^\r\n]+", re.IGNORECASE)),
    ("COOKIE", re.compile(rf"([\"'](?:{_COOKIE_JSON_KEY})[\"']\s*:\s*)(?:[\"'](?:\\.|[^\"'\\\r\n])*[\"']|[^,}}\r\n]+)", re.IGNORECASE)),
    ("COOKIE", re.compile(r"(\b(?:cookies?|session(?:[_-]?id)?)\b\s*[:=]\s*)[^\r\n,;]+", re.IGNORECASE)),
    ("PAYROLL", re.compile(rf"[\"'](?:{_PAYROLL_JSON_KEY})[\"']\s*:\s*[\"']?\d[\d.,]*", re.IGNORECASE)),
    ("PAYROLL", re.compile(r"\b(?:salary|payroll|wage|lương|luong|bảng lương|bang luong)\b[^\n\r]*\d[\d.,]*(?:\s*(?:vnd|vnđ|usd|đ|dollars?))?", re.IGNORECASE)),
)

_VALUE_ONLY_CODES = {"AUTH_TOKEN", "OTP", "COOKIE"}
_ASSIGNMENT_KEYS = {"apikey", "password", "secret"}
_OTP_KEYS = {"otptransactionid"}
_COOKIE_KEYS = {"cookie", "cookies", "session", "sessionid"}


def _normalized_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.casefold())


def _json_key_code(key: str) -> str | None:
    normalized = _normalized_key(key)
    if normalized in _ASSIGNMENT_KEYS:
        return "AUTH_TOKEN"
    if normalized in _OTP_KEYS:
        return "OTP"
    if normalized in _COOKIE_KEYS:
        return "COOKIE"
    if "salary" in normalized or "payroll" in normalized:
        return "PAYROLL"
    return None


def _semantic_codes(text: str) -> tuple[str, ...]:
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


def _json_codes(value) -> tuple[str, ...]:
    codes = []
    seen = set()

    def add(code: str) -> None:
        if code not in seen:
            seen.add(code)
            codes.append(code)

    def walk(item, depth: int = 0) -> None:
        # ponytail: decoded JSON DLP descends three levels; deeper structured subtrees fail closed until streaming/iterative scanning replaces recursion.
        if depth > _JSON_MAX_DEPTH:
            add(_STRUCTURED_DATA_LIMIT)
            return
        if isinstance(item, dict):
            if depth == _JSON_MAX_DEPTH and item:
                add(_STRUCTURED_DATA_LIMIT)
            for key, value in item.items():
                code = _json_key_code(key)
                if code:
                    add(code)
                walk(value, depth + 1)
        elif isinstance(item, list):
            if depth == _JSON_MAX_DEPTH and item:
                add(_STRUCTURED_DATA_LIMIT)
            for value in item:
                walk(value, depth + 1)
        elif isinstance(item, str):
            for code in _semantic_codes(item):
                add(code)
            stripped = item.lstrip()
            if stripped.startswith("﻿"):
                stripped = stripped[1:]
            if stripped[:1] in "[{\"":
                if depth >= _JSON_MAX_DEPTH:
                    add(_STRUCTURED_DATA_LIMIT)
                else:
                    try:
                        walk(json.loads(stripped), depth + 1)
                    except (json.JSONDecodeError, RecursionError):
                        add(_MALFORMED_STRUCTURED_DATA)

    walk(value)
    return tuple(codes)


def _structured_text(text: str) -> str | None:
    stripped = text.lstrip()
    if stripped.startswith("﻿"):
        stripped = stripped[1:]
    return stripped if stripped[:1] in "[{\"" else None


def _decoded_json_codes(text: str) -> tuple[str, ...]:
    structured = _structured_text(text)
    if structured is None:
        return ()
    try:
        return _json_codes(json.loads(structured))
    except (json.JSONDecodeError, RecursionError):
        return (_MALFORMED_STRUCTURED_DATA,)


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
    return _semantic_codes(text)


def sensitivity_gate(text: str) -> SensitivityVerdict:
    codes = _codes(text)
    return SensitivityVerdict(egress_allowed=not codes, codes=codes)


def redact(text: str) -> DlpResult:
    codes = _codes(text)
    if codes and _structured_text(text) is not None:
        markers = ",".join(f"[REDACTED:{code}]" for code in codes)
        return DlpResult(sanitized_text=markers, codes=codes)

    sanitized = text
    for code, pattern in _PATTERNS:
        sanitized = pattern.sub(_replacement(code), sanitized)
    return DlpResult(sanitized_text=sanitized, codes=codes)
