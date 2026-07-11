from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any


def canonical_action_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def issue_confirmation_token(action_id: str, action_hash: str, owner_id: str, tenant_id: str, signing_key: str, ttl_seconds: int) -> tuple[str, datetime]:
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    body = {"action_id": action_id, "action_hash": action_hash, "owner_id": owner_id, "tenant_id": tenant_id, "exp": int(expires_at.timestamp()), "nonce": secrets.token_urlsafe(16)}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    signature = hmac.new(signing_key.encode(), raw, hashlib.sha256).digest()
    return f"{base64.urlsafe_b64encode(raw).decode().rstrip('=')}.{base64.urlsafe_b64encode(signature).decode().rstrip('=')}", expires_at


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verify_confirmation_token(token: str, signing_key: str) -> dict[str, Any]:
    try:
        body_part, signature_part = token.split(".", 1)
        raw = base64.urlsafe_b64decode(body_part + "=" * (-len(body_part) % 4))
        signature = base64.urlsafe_b64decode(signature_part + "=" * (-len(signature_part) % 4))
        expected = hmac.new(signing_key.encode(), raw, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid confirmation signature")
        body = json.loads(raw)
        if int(body["exp"]) <= int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("confirmation expired")
        return body
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid confirmation token") from exc
