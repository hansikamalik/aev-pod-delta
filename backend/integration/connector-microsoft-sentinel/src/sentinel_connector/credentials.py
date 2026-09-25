"""
Credential retrieval, wired through Vault.

Est: 0.5 day (per plan's per-connector standard pattern)

TODO(Harshal): Swap `VaultClientProtocol` / `MockVaultClient` for the
real internal Vault client import, e.g.:

    from platform_vault import VaultClient

The connector code only depends on the `.read_secret(path)` method,
so swapping the implementation should not require touching auth.py
or connector.py.
"""

from typing import Dict, Protocol

from .auth import SentinelAuthConfig

VAULT_PATH_TEMPLATE = "secret/connectors/microsoft-sentinel/{org_id}"


class VaultClientProtocol(Protocol):
    def read_secret(self, path: str) -> Dict[str, str]:
        ...


class MockVaultClient:
    """
    Local stand-in for the real Vault client, used only for tests/dev.
    Replace with the real client in production wiring.
    """

    def __init__(self, fixtures: Dict[str, Dict[str, str]] | None = None):
        self._fixtures = fixtures or {}

    def read_secret(self, path: str) -> Dict[str, str]:
        if path not in self._fixtures:
            raise KeyError(f"No secret at Vault path: {path}")
        return self._fixtures[path]


class CredentialError(Exception):
    pass


REQUIRED_FIELDS = [
    "tenant_id",
    "client_id",
    "client_secret",
    "subscription_id",
    "resource_group",
    "workspace_name",
]


def load_sentinel_credentials(vault: VaultClientProtocol, org_id: str) -> SentinelAuthConfig:
    """
    Fetch Sentinel credentials for a given org from Vault and build a
    SentinelAuthConfig. Raises CredentialError if anything required
    is missing, so callers fail fast rather than hitting Azure AD
    with a half-populated config.
    """
    path = VAULT_PATH_TEMPLATE.format(org_id=org_id)
    secret = vault.read_secret(path)

    missing = [f for f in REQUIRED_FIELDS if not secret.get(f)]
    if missing:
        raise CredentialError(
            f"Vault secret at {path} is missing required fields: {missing}"
        )

    return SentinelAuthConfig(
        tenant_id=secret["tenant_id"],
        client_id=secret["client_id"],
        client_secret=secret["client_secret"],
        subscription_id=secret["subscription_id"],
        resource_group=secret["resource_group"],
        workspace_name=secret["workspace_name"],
    )
