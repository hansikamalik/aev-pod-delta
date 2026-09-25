"""Payload signing and verification.

Signature header format (Stripe/GitHub style, versioned so we can rotate):

    X-AEV-Signature: t=1726550400,v1=<hex hmac-sha256>

The signed string is ``f"{timestamp}.{raw_body}"`` so a captured signature
cannot be replayed against a different body or outside the tolerance window.
Multiple ``v1`` values may be present during secret rotation; any match passes.
"""

from __future__ import annotations

import hashlib
import hmac
import time

SIGNATURE_HEADER = "X-AEV-Signature"
TIMESTAMP_HEADER = "X-AEV-Timestamp"
EVENT_ID_HEADER = "X-AEV-Event-Id"
EVENT_TYPE_HEADER = "X-AEV-Event-Type"
DELIVERY_ID_HEADER = "X-AEV-Delivery-Id"
ATTEMPT_HEADER = "X-AEV-Attempt"


class SignatureError(Exception):
    """Raised when a signature is missing, malformed, stale, or invalid."""


def compute_signature(secret: str, body: bytes, timestamp: int) -> str:
    """Return the hex HMAC-SHA256 of ``{timestamp}.{body}``."""
    signed_payload = f"{timestamp}.".encode() + body
    return hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()


def build_signature_header(secret: str, body: bytes, timestamp: int | None = None) -> tuple[str, int]:
    """Build the header value for an outbound request.

    Returns ``(header_value, timestamp)``.
    """
    ts = int(timestamp if timestamp is not None else time.time())
    return f"t={ts},v1={compute_signature(secret, body, ts)}", ts


def _parse_header(header: str) -> tuple[int, list[str]]:
    timestamp: int | None = None
    signatures: list[str] = []
    for part in header.split(","):
        key, _, value = part.strip().partition("=")
        if key == "t":
            try:
                timestamp = int(value)
            except ValueError as exc:
                raise SignatureError("malformed timestamp in signature header") from exc
        elif key == "v1":
            signatures.append(value)
    if timestamp is None or not signatures:
        raise SignatureError("signature header missing 't' or 'v1'")
    return timestamp, signatures


def verify_signature(
    secret: str,
    body: bytes,
    header: str | None,
    tolerance_seconds: int = 300,
    now: float | None = None,
) -> None:
    """Verify an inbound signature. Raises :class:`SignatureError` on failure.

    ``secret`` may be a comma-separated list during rotation, e.g. ``"new,old"``.
    """
    if not header:
        raise SignatureError("missing signature header")

    timestamp, signatures = _parse_header(header)
    current = int(now if now is not None else time.time())
    if abs(current - timestamp) > tolerance_seconds:
        raise SignatureError("signature timestamp outside tolerance window")

    secrets = [s.strip() for s in secret.split(",") if s.strip()]
    expected = [compute_signature(s, body, timestamp) for s in secrets]

    for candidate in signatures:
        for exp in expected:
            if hmac.compare_digest(candidate, exp):
                return
    raise SignatureError("signature mismatch")
