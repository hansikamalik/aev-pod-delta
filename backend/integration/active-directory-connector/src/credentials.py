"""
Credential retrieval — wires this connector's secret lookup through
Vault (owned by Pod Alpha), per FR-INT-003 (Credential Management:
credentials in Vault; short-lived tokens; rotation).

This connector never reads the service account's bind password from
local config or the environment in production; it only ever reads
`credentials_ref` (a Vault path) from the integration record and
resolves it here.

DEPENDENCY: this module — and therefore the whole connector — cannot
function without network access to Vault. There is no local fallback;
per the platform's dependency table, Vault access fails closed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

import httpx

from .exceptions import VaultAccessError


@dataclass
class ADCredentials:
    bind_password: str
    fetched_at: float
    lease_duration_seconds: int | None = None

    @property
    def is_stale(self) -> bool:
        if self.lease_duration_seconds is None:
            return False
        # Refresh a bit before actual lease expiry.
        return (time.time() - self.fetched_at) >= (self.lease_duration_seconds * 0.8)


class VaultClient(Protocol):
    """Minimal interface this module needs from Alpha's Vault client.
    Implementations (e.g. hvac-based) are provided by the platform's
    shared secrets library and injected at construction time.
    """

    async def read_secret(self, path: str) -> dict: ...


class VaultCredentialProvider:
    """Resolves the AD service account's bind password from Vault via
    `credentials_ref`."""

    def __init__(self, vault_client: VaultClient, credentials_ref: str):
        self._vault = vault_client
        self._credentials_ref = credentials_ref
        self._cached: ADCredentials | None = None

    async def get_credentials(self, *, force_refresh: bool = False) -> ADCredentials:
        if not force_refresh and self._cached is not None and not self._cached.is_stale:
            return self._cached

        try:
            secret = await self._vault.read_secret(self._credentials_ref)
        except httpx.HTTPError as exc:
            raise VaultAccessError(
                f"Vault unreachable while resolving '{self._credentials_ref}': {exc}"
            ) from exc
        except Exception as exc:  # noqa: BLE001 - normalize any client-specific error
            raise VaultAccessError(
                f"Failed to read credentials at '{self._credentials_ref}': {exc}"
            ) from exc

        bind_password = secret.get("bind_password")
        if not bind_password:
            raise VaultAccessError(
                f"Vault secret at '{self._credentials_ref}' is missing 'bind_password'"
            )

        self._cached = ADCredentials(
            bind_password=bind_password,
            fetched_at=time.time(),
            lease_duration_seconds=secret.get("lease_duration"),
        )
        return self._cached

    def invalidate(self) -> None:
        """Force the next get_credentials() call to hit Vault again —
        used after a rotation event or a bind failure."""
        self._cached = None
