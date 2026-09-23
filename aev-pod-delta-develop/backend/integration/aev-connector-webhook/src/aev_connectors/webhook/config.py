"""Configuration for the custom Webhook connector.

Secrets are never read from the environment in production: they are resolved
through Vault via `aev_connectors.common.vault`. The env vars below are a local
development fallback only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

DEFAULT_EVENT_TYPES: tuple[str, ...] = (
    "asset.created",
    "asset.updated",
    "asset.deleted",
    "exposure.created",
    "exposure.resolved",
    "finding.created",
    "scan.completed",
)


@dataclass(frozen=True)
class RetryPolicy:
    """Exponential backoff with full jitter."""

    max_attempts: int = 6
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 300.0
    multiplier: float = 2.0
    jitter: bool = True
    # HTTP status codes that are worth retrying.
    retry_status_codes: frozenset[int] = field(
        default_factory=lambda: frozenset({408, 425, 429, 500, 502, 503, 504})
    )

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.base_delay_seconds <= 0:
            raise ValueError("base_delay_seconds must be > 0")


@dataclass(frozen=True)
class WebhookConfig:
    """Per-tenant configuration for one registered webhook endpoint."""

    org_id: str
    connector_id: str
    target_url: str
    signing_secret: str
    auth_mode: str = "hmac"  # hmac | bearer | basic | none
    auth_token: str | None = None
    basic_username: str | None = None
    basic_password: str | None = None
    timeout_seconds: float = 10.0
    signature_tolerance_seconds: int = 300
    verify_tls: bool = True
    retry: RetryPolicy = field(default_factory=RetryPolicy)

    VALID_AUTH_MODES = ("hmac", "bearer", "basic", "none")

    def __post_init__(self) -> None:
        if not self.target_url.startswith(("http://", "https://")):
            raise ValueError("target_url must be an absolute http(s) URL")
        if self.auth_mode not in self.VALID_AUTH_MODES:
            raise ValueError(f"auth_mode must be one of {self.VALID_AUTH_MODES}")
        if self.auth_mode == "bearer" and not self.auth_token:
            raise ValueError("auth_token is required when auth_mode='bearer'")
        if self.auth_mode == "basic" and not (self.basic_username and self.basic_password):
            raise ValueError("basic_username/basic_password required when auth_mode='basic'")
        if not self.signing_secret:
            raise ValueError("signing_secret is required")

    @classmethod
    def from_env(cls, org_id: str = "local-dev") -> WebhookConfig:
        """Local development helper. Not used in staging or production."""
        return cls(
            org_id=org_id,
            connector_id=os.getenv("WEBHOOK_CONNECTOR_ID", "webhook-custom-local"),
            target_url=os.getenv("WEBHOOK_TARGET_URL", "http://localhost:9000/hook"),
            signing_secret=os.getenv("WEBHOOK_SIGNING_SECRET", "dev-secret-change-me"),
            auth_mode=os.getenv("WEBHOOK_AUTH_MODE", "hmac"),
            auth_token=os.getenv("WEBHOOK_AUTH_TOKEN"),
            basic_username=os.getenv("WEBHOOK_BASIC_USER"),
            basic_password=os.getenv("WEBHOOK_BASIC_PASS"),
            verify_tls=os.getenv("WEBHOOK_VERIFY_TLS", "true").lower() != "false",
        )
