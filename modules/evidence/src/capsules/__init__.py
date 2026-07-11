from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable


@dataclass(frozen=True)
class EvidenceCapsule:
    capsule_id: str
    run_id: str
    tenant_id: str
    purpose: str
    source_type: str
    source_id: str
    source_version: str
    evidence_id: str
    span_locator: dict[str, Any]
    span_hash: str
    classification: str
    policy_decision_id: str
    acl_scope_hash: str
    sanitized_content: str
    issued_at: datetime
    expires_at: datetime
    integrity_tag: str

    def outbound_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "content": self.sanitized_content,
            "source_type": self.source_type,
        }


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _tag(fields: dict[str, Any], signing_key: str) -> str:
    return hmac.new(signing_key.encode(), _canonical(fields), hashlib.sha256).hexdigest()


def build_capsule(
    chunks: Iterable[dict[str, Any]],
    *,
    run_id: str = "offline",
    tenant_id: str = "offline",
    purpose: str = "KNOWLEDGE_SEARCH",
    signing_key: str = "offline-test-key",
    ttl_seconds: int = 300,
) -> tuple[EvidenceCapsule, ...]:
    """Create immutable, manifest-ready capsules from already-authorized chunks."""
    now = datetime.now(timezone.utc)
    capsules: list[EvidenceCapsule] = []
    for chunk in chunks:
        content = str(chunk.get("sanitized_content", chunk.get("content", "")))
        if not content:
            continue
        source_id = str(chunk.get("source_id") or chunk.get("document_id") or "")
        version = str(chunk.get("source_version") or chunk.get("version_id") or "")
        span_hash = hashlib.sha256(content.encode()).hexdigest()
        evidence_identity = hashlib.sha256(f"{source_id}:{version}:{span_hash}".encode()).hexdigest()
        evidence_id = str(chunk.get("evidence_id") or f"ev_{evidence_identity[:24]}")
        span_locator = dict(chunk.get("span_locator") or {})
        fields = {
            "capsule_id": str(uuid.uuid4()),
            "run_id": run_id,
            "tenant_id": tenant_id,
            "purpose": purpose,
            "source_type": str(chunk.get("source_type", "DOCUMENT")),
            "source_id": source_id,
            "source_version": version,
            "evidence_id": evidence_id,
            "span_locator": span_locator,
            "span_hash": span_hash,
            "classification": str(chunk.get("classification", "Internal")),
            "policy_decision_id": str(chunk.get("policy_decision_id") or ""),
            "acl_scope_hash": str(chunk.get("acl_scope_hash") or hashlib.sha256(b"default").hexdigest()),
            "sanitized_content": content,
            "issued_at": now,
            "expires_at": now + timedelta(seconds=ttl_seconds),
        }
        capsules.append(EvidenceCapsule(
            capsule_id=str(fields["capsule_id"]), run_id=str(fields["run_id"]),
            tenant_id=str(fields["tenant_id"]), purpose=str(fields["purpose"]),
            source_type=str(fields["source_type"]), source_id=str(fields["source_id"]),
            source_version=str(fields["source_version"]), evidence_id=str(fields["evidence_id"]),
            span_locator=span_locator, span_hash=str(fields["span_hash"]),
            classification=str(fields["classification"]),
            policy_decision_id=str(fields["policy_decision_id"]),
            acl_scope_hash=str(fields["acl_scope_hash"]),
            sanitized_content=str(fields["sanitized_content"]),
            issued_at=now, expires_at=now + timedelta(seconds=ttl_seconds),
            integrity_tag=_tag(fields, signing_key),
        ))
    return tuple(capsules)


def validate_capsule(capsule: EvidenceCapsule, signing_key: str, *, now: datetime | None = None) -> bool:
    moment = now or datetime.now(timezone.utc)
    if capsule.expires_at <= moment:
        return False
    fields = asdict(capsule)
    tag = fields.pop("integrity_tag")
    return hmac.compare_digest(tag, _tag(fields, signing_key))
