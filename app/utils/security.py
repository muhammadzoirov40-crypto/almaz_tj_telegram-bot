from __future__ import annotations

import hashlib
import hmac
import secrets


def generate_idempotency_key(length: int = 32) -> str:
    return secrets.token_hex(length // 2)


def sign_payload(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not secret:
        return False
    expected = sign_payload(payload, secret)
    return hmac.compare_digest(expected, signature)


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)
