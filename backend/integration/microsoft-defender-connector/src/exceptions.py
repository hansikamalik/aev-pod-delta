class DefenderConnectorError(Exception):
    """Base exception for all Microsoft Defender connector errors."""


class AuthenticationError(DefenderConnectorError):
    """Raised when OAuth 2.0 token acquisition fails."""


class VaultAccessError(DefenderConnectorError):
    """Raised when connector credentials cannot be retrieved from Vault.

    This connector cannot authenticate to Microsoft Defender without
    Vault access — the client_secret referenced by
    IntegrationConfig.credentials_ref lives in Vault (Alpha), never in
    connector config. See README.md > Dependencies.
    """


class DefenderAPIError(DefenderConnectorError):
    """Raised when the Microsoft Defender for Endpoint API returns an
    unexpected response (non-2xx, malformed payload, rate limit)."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class PushError(DefenderConnectorError):
    """Raised when pushing normalized assets/findings to the platform's
    Asset/Exposure services (Beta) fails."""
