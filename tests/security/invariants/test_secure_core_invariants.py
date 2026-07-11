from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from modules.evidence.src.capsules import build_capsule, validate_capsule
from modules.guardrails.src.answer_validation import AnswerValidationError, validate_answer
from modules.guardrails.src.egress.inspector import EgressSegment, EgressSpy, dispatch_if_allowed, inspect_egress
from modules.identity.src.subject import SubjectContext
from modules.policy.src.engine import PolicyEngine
from modules.tools.src.mocks import default_mock_registry


@pytest.mark.asyncio
async def test_s1_s8_cross_tenant_policy_is_fail_closed() -> None:
    subject = SubjectContext("tenant-a", "user-a", roles=("Employee",), departments=("HR",))
    decision = await PolicyEngine().decide(subject, {"tenant_id": "tenant-b", "classification": "Public"}, "knowledge:read")
    assert decision.decision.value == "DENY"


def test_s2_s3_s4_s11_sensitive_or_unattributed_egress_never_dispatches() -> None:
    spy = EgressSpy()
    assert not dispatch_if_allowed("salary: 2500 USD", [EgressSegment("PROMPT_TEMPLATE", "safe", "p1")], spy).allowed
    assert not dispatch_if_allowed("safe", [EgressSegment("EVIDENCE_CAPSULE", "Bearer secret-token", "ev1")], spy).allowed
    assert not inspect_egress([EgressSegment("UNKNOWN", "safe", "")]).allowed
    assert spy.calls == ()


def test_s5_unknown_tool_cannot_execute() -> None:
    with pytest.raises(KeyError, match="unknown or disabled tool"):
        default_mock_registry().get("arbitrary_http")


@pytest.mark.asyncio
async def test_s9_payroll_requires_active_step_up() -> None:
    subject = SubjectContext("tenant", "user", roles=("Employee",), departments=("HR",))
    decision = await PolicyEngine().decide(subject, {"tenant_id": "tenant", "classification": "Restricted"}, "tool:payroll", "SELF_PAYROLL_READ")
    assert decision.reason == "STEP_UP_REQUIRED"


def test_s7_citations_are_limited_to_manifest() -> None:
    capsule = build_capsule([{"document_id": "D1", "version_id": "V1", "content": "policy", "policy_decision_id": "P1"}])[0]
    with pytest.raises(AnswerValidationError, match="citation outside manifest"):
        validate_answer({"status": "ANSWER", "answer": "claim", "claims": [{"claim_id": "c1", "text": "claim", "evidence_ids": ["invented"]}], "confidence": "LOW"}, [capsule])


def test_s10_model_contract_contains_no_reasoning_or_chain_of_thought_field() -> None:
    from modules.agent.src.runtime import ANSWER_SCHEMA
    assert "reasoning" not in ANSWER_SCHEMA["properties"]
    assert "chain_of_thought" not in ANSWER_SCHEMA["properties"]


def test_s12_expired_capsules_are_invalid() -> None:
    capsule = build_capsule([{"document_id": "D1", "version_id": "V1", "content": "policy", "policy_decision_id": "P1"}], signing_key="key")[0]
    expired = replace(capsule, expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    assert not validate_capsule(expired, "key")


def test_s6_confirmation_execution_requires_signed_token_contract() -> None:
    from modules.tools.src.actions import canonical_action_hash, issue_confirmation_token, verify_confirmation_token
    action_hash = canonical_action_hash({"action": "submit", "target": "self"})
    token, _ = issue_confirmation_token("A1", action_hash, "U1", "T1", "key", 60)
    claims = verify_confirmation_token(token, "key")
    assert claims["action_id"] == "A1"
    assert claims["action_hash"] == action_hash
