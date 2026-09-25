"""
Secrets Vault integration
Owner: Abhiram
Part of: Shared Integration Infrastructure

Design notes:
- Generic credential retrieval interface so any connector (Azure, Splunk,
  or a dummy test connector) fetches secrets the same way; no connector
  ever hardcodes credentials.
- Backed by a MOCK vault (in-memory) for independent development. Swap
  `MockVaultBackend` for a real backend (e.g. HashiCorp Vault, Azure Key
  Vault) later — `SecretsVaultClient` itself never changes.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger("secrets_vault")


class VaultError(Exception):
    """Base vault error."""


class SecretNotFoundError(VaultError):
    pass


class VaultUnavailableError(VaultError):
    """Retryable — vault backend temporarily unreachable."""


class MockVaultBackend:
    """In-memory stand-in for a real secrets backend."""

    def __init__(self, seed_secrets: Optional[dict] = None, unavailable_for_n_calls: int = 0):
        self._store = dict(seed_secrets or {})
        self._unavailable_for_n_calls = unavailable_for_n_calls
        self._calls = 0

    def get(self, key: str) -> str:
        self._calls += 1
        if self._calls <= self._unavailable_for_n_calls:
            raise VaultUnavailableError("Vault backend temporarily unreachable")
        if key not in self._store:
            raise SecretNotFoundError(f"No secret found for key '{key}'")
        return self._store[key]

    def put(self, key: str, value: str) -> None:
        self._store[key] = value


class SecretsVaultClient:
    """
    Generic credential retrieval used by every connector.
    Example: vault.get_credential("azure/service-principal/tenant-a")
    """

    def __init__(self, backend, max_retries: int = 3, backoff_base_seconds: float = 0.2):
        self.backend = backend
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds
        self._cache: dict = {}

    def get_credential(self, key: str, use_cache: bool = True) -> str:
        if use_cache and key in self._cache:
            return self._cache[key]

        attempt = 0
        while True:
            try:
                value = self.backend.get(key)
                self._cache[key] = value
                return value
            except VaultUnavailableError as exc:
                attempt += 1
                if attempt > self.max_retries:
                    logger.error("Vault unavailable for '%s' after %d attempts", key, attempt)
                    raise
                sleep_for = self.backoff_base_seconds * (2 ** (attempt - 1))
                logger.warning("Vault unavailable (attempt %d/%d): %s — retrying in %.2fs",
                               attempt, self.max_retries, exc, sleep_for)
                time.sleep(sleep_for)
            except SecretNotFoundError:
                logger.error("Secret not found: %s", key)
                raise

    def put_credential(self, key: str, value: str) -> None:
        self.backend.put(key, value)
        self._cache.pop(key, None)

    def invalidate_cache(self, key: Optional[str] = None) -> None:
        if key is None:
            self._cache.clear()
        else:
            self._cache.pop(key, None)
