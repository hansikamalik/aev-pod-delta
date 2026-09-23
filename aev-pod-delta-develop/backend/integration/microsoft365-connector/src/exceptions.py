class ConnectorError(Exception):
    """Base class for all Microsoft 365 connector errors."""


class AuthenticationError(ConnectorError):
    """Raised when acquiring a Graph API token fails."""


class DiscoveryError(ConnectorError):
    """Raised when a Graph API discovery call fails."""


class NormalizationError(ConnectorError):
    """Raised when a raw Graph object can't be mapped to the shared Asset shape."""


class PushError(ConnectorError):
    """Raised when pushing normalized assets to the platform fails."""


class VaultError(ConnectorError):
    """Raised when a credential can't be retrieved from Vault."""
