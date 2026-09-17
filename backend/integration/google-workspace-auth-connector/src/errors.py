class OAuthError(Exception):
    """An expected, safe-to-display OAuth failure."""

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code
