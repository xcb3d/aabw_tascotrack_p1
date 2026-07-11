from dataclasses import dataclass


@dataclass(frozen=True)
class SensitivityVerdict:
    egress_allowed: bool
    codes: tuple[str, ...]


@dataclass(frozen=True)
class DlpResult:
    sanitized_text: str
    codes: tuple[str, ...]


@dataclass(frozen=True)
class EgressDecision:
    allowed: bool
    code: str
