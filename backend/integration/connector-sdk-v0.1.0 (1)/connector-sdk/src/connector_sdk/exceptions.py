"""Shared exception hierarchy for the Connector SDK.

Contract reference: Section 16 (Error Handling).

Rules enforced by this module's design:
  * Connectors MUST NOT silently swallow errors.
  * Errors SHOULD carry enough context to diagnose the problem
    (operation, source, resource identifier, API status, timestamp).
  * Credentials and secrets MUST NEVER appear in an error message.

Transient vs permanent is expressed by the ``retryable`` attribute so that
retry/backoff helpers and the scheduler can make a decision without
string-matching on messages.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ConnectorError(Exception):
    """Base class for every error raised by a connector or by the SDK.

    Parameters
    ----------
    message:
        Human-readable description. MUST NOT contain secrets.
    operation:
        Logical operation that failed, e.g. ``"discover"``, ``"ingest"``,
        ``"check_health"``, ``"authenticate"``.
    source:
        Connector name, e.g. ``"azure"``.
    resource_id:
        Identifier of the specific resource involved, when applicable.
    status_code:
        HTTP / API status code, when applicable.
    retryable:
        Whether retrying the operation could reasonably succeed.
    """

    retryable: bool = False

    def __init__(
        self,
        message: str,
        *,
        operation: str | None = None,
        source: str | None = None,
        resource_id: str | None = None,
        status_code: int | None = None,
        retryable: bool | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.operation = operation
        self.source = source
        self.resource_id = resource_id
        self.status_code = status_code
        self.details = details or {}
        self.occurred_at = _utcnow()
        if retryable is not None:
            self.retryable = retryable

    def to_dict(self) -> dict[str, Any]:
        """Serialize for ``SyncResult.errors`` and structured logging."""
        return {
            "error_type": type(self).__name__,
            "message": self.message,
            "operation": self.operation,
            "source": self.source,
            "resource_id": self.resource_id,
            "status_code": self.status_code,
            "retryable": self.retryable,
            "occurred_at": self.occurred_at.isoformat(),
            "details": self.details,
        }

    def __str__(self) -> str:
        parts = [self.message]
        context = {
            "operation": self.operation,
            "source": self.source,
            "resource_id": self.resource_id,
            "status": self.status_code,
        }
        rendered = " ".join(f"{k}={v}" for k, v in context.items() if v is not None)
        if rendered:
            parts.append(f"({rendered})")
        return " ".join(parts)


# --------------------------------------------------------------------------
# Configuration / credentials
# --------------------------------------------------------------------------


class ConfigurationError(ConnectorError):
    """Connector configuration is missing, malformed, or invalid.

    Permanent: retrying with the same configuration cannot succeed.
    """


class CredentialError(ConnectorError):
    """A required credential is missing or malformed.

    Never include the credential value itself in the message.
    """


class AuthenticationError(ConnectorError):
    """The source system rejected the supplied credentials (401 / 403).

    Permanent by contract (Section 22): do not blindly retry.
    """


# --------------------------------------------------------------------------
# Source-system communication
# --------------------------------------------------------------------------


class SourceError(ConnectorError):
    """Generic failure while talking to the external source system."""


class SourceUnavailableError(SourceError):
    """Source is unreachable or returned 502 / 503 / 504. Transient."""

    retryable = True


class RateLimitError(SourceError):
    """Source returned HTTP 429. Transient.

    ``retry_after`` carries the server-advertised backoff in seconds when
    the source provides it.
    """

    retryable = True

    def __init__(self, message: str, *, retry_after: float | None = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload["retry_after"] = self.retry_after
        return payload


class DiscoveryError(SourceError):
    """Discovery failed for the source system or for a specific resource."""


# --------------------------------------------------------------------------
# Platform side
# --------------------------------------------------------------------------


class IngestionError(ConnectorError):
    """The platform rejected one or more assets during ingestion.

    An asset MUST NOT be reported as pushed if the platform rejected it
    (Section 11).
    """


class ValidationError(ConnectorError):
    """An Asset or schema failed SDK-side validation before leaving the connector."""


class ContractViolation(ConnectorError):
    """A connector implementation breaks the SDK contract.

    Raised by the SDK itself (and by the shared contract tests), not by
    normal source-system failures.
    """


__all__ = [
    "ConnectorError",
    "ConfigurationError",
    "CredentialError",
    "AuthenticationError",
    "SourceError",
    "SourceUnavailableError",
    "RateLimitError",
    "DiscoveryError",
    "IngestionError",
    "ValidationError",
    "ContractViolation",
]
