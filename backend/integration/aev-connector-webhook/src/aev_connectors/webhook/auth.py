"""Outbound auth headers and inbound auth verification.

Credentials are resolved through Vault by the caller and handed to
:class:`~aev_connectors.webhook.config.WebhookConfig`; nothing here touches a
secret store directly.
"""

from __future__ import annotations

import base64
import hmac

from .config import WebhookConfig
from .signing import SIGNATURE_HEADER, SignatureError, build_signature_header, verify_signature


class AuthError(Exception):
    """Raised when inbound auth fails."""


def build_auth_headers(config: WebhookConfig, body: bytes) -> dict[str, str]:
    """Return the auth/signature headers for one outbound delivery."""
    headers: dict[str, str] = {}

    if config.auth_mode == "bearer":
        headers["Authorization"] = f"Bearer {config.auth_token}"
    elif config.auth_mode == "basic":
        raw = f"{config.basic_username}:{config.basic_password}".encode()
        headers["Authorization"] = "Basic " + base64.b64encode(raw).decode()

    # Every outbound delivery is signed, regardless of auth_mode, so the
    # receiver can verify integrity independently of transport auth.
    value, ts = build_signature_header(config.signing_secret, body)
    headers[SIGNATURE_HEADER] = value
    headers["X-AEV-Timestamp"] = str(ts)
    return headers


def verify_inbound(
    config: WebhookConfig,
    body: bytes,
    headers: dict[str, str],
) -> None:
    """Verify an inbound request against the connector's configured auth mode.

    Header lookup is case-insensitive. Raises :class:`AuthError`.
    """
    lowered = {k.lower(): v for k, v in headers.items()}

    if config.auth_mode == "bearer":
        provided = lowered.get("authorization", "")
        expected = f"Bearer {config.auth_token}"
        if not hmac.compare_digest(provided, expected):
            raise AuthError("invalid bearer token")
    elif config.auth_mode == "basic":
        raw = f"{config.basic_username}:{config.basic_password}".encode()
        expected = "Basic " + base64.b64encode(raw).decode()
        if not hmac.compare_digest(lowered.get("authorization", ""), expected):
            raise AuthError("invalid basic credentials")

    if config.auth_mode in ("hmac", "bearer", "basic"):
        try:
            verify_signature(
                config.signing_secret,
                body,
                lowered.get(SIGNATURE_HEADER.lower()),
                tolerance_seconds=config.signature_tolerance_seconds,
            )
        except SignatureError as exc:
            raise AuthError(str(exc)) from exc
