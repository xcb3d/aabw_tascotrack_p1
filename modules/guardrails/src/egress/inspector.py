from dataclasses import dataclass

from modules.guardrails.contracts.verdicts import EgressDecision
from modules.guardrails.src.dlp.screening import sensitivity_gate


_ALLOWED_ORIGINS = {"PROMPT_TEMPLATE", "SANITIZED_QUERY", "EVIDENCE_CAPSULE", "TOOL_DEFINITION"}


@dataclass(frozen=True)
class EgressSegment:
    origin: str
    content: str
    reference: str


class EgressSpy:
    def __init__(self):
        self.calls: tuple[tuple[EgressSegment, ...], ...] = ()

    def __call__(self, segments):
        self.calls += (tuple(segments),)


def _materialized_segments(segments):
    snapshot = []
    for segment in segments:
        origin, content, reference = segment.origin, segment.content, segment.reference
        if not all(isinstance(value, str) for value in (origin, content, reference)):
            raise TypeError("egress segment fields must be strings")
        snapshot.append(EgressSegment(str(origin), str(content), str(reference)))
    return tuple(snapshot)


def inspect_egress(segments):
    try:
        snapshot = _materialized_segments(segments)
    except (AttributeError, TypeError):
        return EgressDecision(False, "UNATTRIBUTED_SEGMENT")
    if not snapshot:
        return EgressDecision(False, "UNATTRIBUTED_SEGMENT")
    if any(segment.origin not in _ALLOWED_ORIGINS or not segment.reference for segment in snapshot):
        return EgressDecision(False, "UNATTRIBUTED_SEGMENT")
    return EgressDecision(True, "ALLOWED")


def dispatch_if_allowed(user_query, segments, send):
    try:
        snapshot = _materialized_segments(segments)
    except (AttributeError, TypeError):
        return EgressDecision(False, "UNATTRIBUTED_SEGMENT")
    if not sensitivity_gate(user_query).egress_allowed:
        return EgressDecision(False, "SENSITIVITY_DENIED")
    # ponytail: all materialized segment contents are screened until registry attribution and content hashes can prove trusted origins.
    if any(not sensitivity_gate(segment.content).egress_allowed for segment in snapshot):
        return EgressDecision(False, "SENSITIVITY_DENIED")
    decision = inspect_egress(snapshot)
    if not decision.allowed:
        return decision
    send(snapshot)
    return decision
