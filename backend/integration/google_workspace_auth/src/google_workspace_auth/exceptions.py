class AuthenticationError(Exception):
    """Raised when Google authentication cannot produce a valid access token."""


class ConfigurationError(ValueError):
    """Raised when required authentication configuration is invalid."""
