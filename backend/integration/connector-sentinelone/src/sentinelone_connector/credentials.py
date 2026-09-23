"""
Credential retrieval, wired through Vault.

Est: 0.5 day (per plan's per-connector standard pattern)

TODO(Bhavesh): Swap `VaultClientProtocol` / `MockVaultClient` for the
real internal Vault client (same swap as the Sentinel connector). The
connector only depends on `.read_secret(path)`.
"""

from typing import Dict, Protocol

from .auth import SentinelOneAuthConfig

VAULT_PATH_TEMPLATE = "secret/connectors/sentinelone/{org_id}"

REQUIRED_FIELDS = ["base_url", "api_token"]


class VaultClientProtocol(Protocol):
    def read_secret(self, path: str) -> Dict[str, str]:
        ...


class MockVaultClient:
    """Local stand-in for the real Vault client, used only for tests/dev."""

    def __init__(self, fixtures: Dict[str, Dict[str, str]] | None = None):
        self._fixtures = fixtures or {}

    def read_secret(self, path: str) -> Dict[str, str]:
        if path not in self._fixtures:
            raise KeyError(f"No secret at Vault path: {path}")
        return self._fixtures[path]


class CredentialError(Exception):
    pass


def load_sentinelone_credentials(vault: VaultClientProtocol, org_id: str) -> SentinelOneAuthConfig:
    """Fail fast with CredentialError if the Vault secret is incomplete."""
    path = VAULT_PATH_TEMPLATE.format(org_id=org_id)
    secret = vault.read_secret(path)

    missing = [f for f in REQUIRED_FIELDS if not secret.get(f)]
    if missing:
        raise CredentialError(f"Vault secret at {path} is missing required fields: {missing}")

    base_url = secret["base_url"]
    if not base_url.startswith("https://"):
        raise CredentialError(f"Vault secret at {path}: base_url must start with https://")

    return SentinelOneAuthConfig(base_url=base_url, api_token=secret["api_token"])
