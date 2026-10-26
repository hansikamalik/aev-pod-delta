"""
Domain exception hierarchy for the Connector SDK.

Unifies error reporting across all cloud and endpoint connectors.
Provides consistent structured attributes (operation, source, resource_id).
"""

from __future__ import annotations

from typing import Optional


class ConnectorError(Exception):
    """Base exception for all connector runtime and contract errors."""

    def __init__(
        self,
        message: str = "",
        operation: Optional[str] = None,
        source: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.operation = operation
        self.source = source
        self.resource_id = resource_id

    def __str__(self) -> str:
        parts = [self.message or type(self).__name__]
        details = []
        if self.operation:
            details.append(f"operation={self.operation}")
        if self.source:
            details.append(f"source={self.source}")
        if self.resource_id:
            details.append(f"resource_id={self.resource_id}")
        if details:
            parts.append(f"({', '.join(details)})")
        return " ".join(parts)


class ConfigurationError(ConnectorError):
    """Raised when connector configuration is missing, malformed, or invalid."""


class CredentialError(ConnectorError):
    """Raised when authentication credentials (API key, tokens, certs) are invalid."""


class AuthenticationError(CredentialError):
    """Raised when authentication with the remote target service fails."""


class SourceError(ConnectorError):
    """Raised when the remote target service encounters an unrecoverable API/network error."""


class DiscoveryError(ConnectorError):
    """Raised during the asset discovery phase."""


class IngestionError(ConnectorError):
    """Raised when pushing or normalizing discovered assets fails."""


class ValidationError(ConnectorError):
    """Raised when an asset or schema contract validation fails."""


class ContractViolation(ConnectorError):
    """Raised when a connector violates the mandatory SDK lifecycle contract."""
