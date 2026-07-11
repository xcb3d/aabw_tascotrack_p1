from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
import re

from modules.evidence.src.capsules import EvidenceCapsule
from modules.guardrails.src.dlp.screening import sensitivity_gate


@dataclass(frozen=True)
class ValidatedAnswer:
    status: str
    answer: str
    claims: tuple[dict[str, Any], ...]
    evidence_ids: tuple[str, ...]
    confidence: str


class AnswerValidationError(ValueError):
    pass


def validate_answer(output: dict[str, Any], capsules: Iterable[EvidenceCapsule]) -> ValidatedAnswer:
    allowed = {capsule.evidence_id for capsule in capsules}
    status = str(output.get("status", ""))
    if status == "INSUFFICIENT_EVIDENCE":
        return ValidatedAnswer(status, "", (), (), "LOW")
    if status != "ANSWER":
        raise AnswerValidationError("unknown answer status")
    answer = output.get("answer")
    claims = output.get("claims")
    if not isinstance(answer, str) or not answer.strip() or not isinstance(claims, list) or not claims:
        raise AnswerValidationError("answer and claims are required")
    if not sensitivity_gate(answer).egress_allowed:
        raise AnswerValidationError("answer failed output DLP")
    used: list[str] = []
    clean_claims: list[dict[str, Any]] = []
    for claim in claims:
        if not isinstance(claim, dict) or not isinstance(claim.get("text"), str):
            raise AnswerValidationError("invalid claim")
        ids = claim.get("evidence_ids")
        if not isinstance(ids, list) or not ids or not all(isinstance(item, str) for item in ids):
            raise AnswerValidationError("every claim requires evidence IDs")
        if not set(ids).issubset(allowed):
            raise AnswerValidationError("citation outside manifest")
        if not sensitivity_gate(claim["text"]).egress_allowed:
            raise AnswerValidationError("claim failed output DLP")
        cited_text = " ".join(capsule.sanitized_content for capsule in capsules if capsule.evidence_id in ids)
        numbers = re.findall(r"\b\d+(?:[.,]\d+)*\b", claim["text"])
        if any(number not in cited_text for number in numbers):
            raise AnswerValidationError("claim contains an unsupported numeric or date value")
        used.extend(ids)
        clean_claims.append(
            {"claimId": str(claim.get("claim_id") or f"claim-{len(clean_claims) + 1}"), "text": claim["text"], "evidenceIds": ids}
        )
    return ValidatedAnswer(
        status="ANSWER",
        answer=answer.strip(),
        claims=tuple(clean_claims),
        evidence_ids=tuple(dict.fromkeys(used)),
        confidence=str(output.get("confidence", "MEDIUM")),
    )
