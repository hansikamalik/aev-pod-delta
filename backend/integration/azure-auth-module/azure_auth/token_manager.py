"""
Token acquisition, caching, and refresh.

Consumers (Discovery, Normalization/Push) should never call Azure AD
directly for a token — they should ask AzureAuthenticator for one, which
delegates here. This keeps token lifetime/refresh logic in one place.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional

from .exceptions import TokenExpiredError

# Refresh this many seconds *before* actual expiry, to avoid handing out
# a token that dies mid-request.
REFRESH_SKEW_SECONDS = 60


@dataclass
class Token:
    access_token: str
    expires_at: float  # unix timestamp
    scope: str = "https://management.azure.com/.default"

    def is_expired(self, *, skew: int = REFRESH_SKEW_SECONDS) -> bool:
        return time.time() >= (self.expires_at - skew)


class TokenManager:
    """Caches a single Azure AD token and refreshes it on demand.

    `fetch_fn` is injected so this class has no direct dependency on the
    Azure SDK or network calls — makes it trivially unit-testable and
    lets MockAzureAuthenticator reuse it with a fake fetch function.
    """

    def __init__(self, fetch_fn: Callable[[], Token]):
        self._fetch_fn = fetch_fn
        self._cached: Optional[Token] = None

    def get_token(self, *, force_refresh: bool = False) -> Token:
        if force_refresh or self._cached is None or self._cached.is_expired():
            self._cached = self._fetch_fn()
        return self._cached

    def invalidate(self) -> None:
        self._cached = None

    def peek(self) -> Optional[Token]:
        """Return the cached token without triggering a refresh, or None."""
        return self._cached

    @staticmethod
    def assert_not_expired(token: Token) -> None:
        if token.is_expired(skew=0):
            raise TokenExpiredError()
