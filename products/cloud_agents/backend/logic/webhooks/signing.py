"""Webhook signatures.

A receiver checks a delivery with the same steps as `verify`: take the raw request body, prefix it
with the `X-PostHog-Webhook-Timestamp` value and a dot, compute HMAC-SHA256 with the webhook secret,
and compare the hex digest with the `v1=` value of `X-PostHog-Webhook-Signature`.
"""

from __future__ import annotations

import hmac
import hashlib
import secrets
from typing import Final

SECRET_PREFIX: Final = "whsec_"
SIGNATURE_VERSION: Final = "v1"


def generate_secret() -> str:
    return f"{SECRET_PREFIX}{secrets.token_urlsafe(32)}"


def sign(secret: str, timestamp: int | str, body: bytes) -> str:
    signed = f"{timestamp}.".encode() + body
    return hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()


def verify(secret: str, timestamp: int | str, body: bytes, signature: str) -> bool:
    """`signature` is the hex digest, with or without the `v1=` prefix."""
    expected = sign(secret, timestamp, body)
    return hmac.compare_digest(expected, signature.removeprefix(f"{SIGNATURE_VERSION}="))
