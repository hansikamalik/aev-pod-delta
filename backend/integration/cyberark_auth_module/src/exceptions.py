class CyberArkAuthError(Exception):
    """Base exception raised for CyberArk authentication failures."""
    pass


class CyberArkTokenExpiredError(CyberArkAuthError):
    """Raised when an active session or OAuth token has expired."""
    pass
