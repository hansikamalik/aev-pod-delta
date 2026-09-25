"""
Authentication error hierarchy.

All errors raised by this module inherit from AuthenticationError so
downstream consumers (Discovery, Normalization, QA) can catch broadly
with `except AuthenticationError` or narrowly by specific type.
"""


class AuthenticationError(Exception):
    """Base class for all authentication-related errors."""

    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.retryable = retryable


class InvalidCredentialsError(AuthenticationError):
    """Raised when service-principal credentials are missing or malformed."""

    def __init__(self, message: str = "Invalid or incomplete Azure credentials"):
        super().__init__(message, retryable=False)


class CredentialValidationError(AuthenticationError):
    """Raised when credentials are well-formed but rejected by Azure AD."""

    def __init__(self, message: str = "Azure AD rejected the provided credentials"):
        super().__init__(message, retryable=False)


class TokenExpiredError(AuthenticationError):
    """Raised when a cached token has expired and refresh failed."""

    def __init__(self, message: str = "Azure access token has expired"):
        super().__init__(message, retryable=True)


class ThrottledError(AuthenticationError):
    """Raised when Azure AD throttles the authentication request (HTTP 429)."""

    def __init__(self, message: str = "Azure AD throttled the request", retry_after: int = 30):
        super().__init__(message, retryable=True)
        self.retry_after = retry_after
