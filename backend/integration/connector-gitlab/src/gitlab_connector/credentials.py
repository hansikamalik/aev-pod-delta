"""
Credential retrieval, wired through Vault.

Est: 0.5 day (per plan's per-connector standard pattern)

TODO(Bhavesh): Swap `VaultClientProtocol` / `MockVaultClient` for the
real internal Vault client (same swap as the other connectors).
"""

from typing import Dict, Protocol

from .auth import DEFAULT_API_URL, GitLabAuthConfig

VAULT_PATH_TEMPLATE = "secret/connectors/gitlab/{org_id}"

REQUIRED_FIELDS = ["token", "group"]


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


def load_gitlab_credentials(vault: VaultClientProtocol, org_id: str) -> GitLabAuthConfig:
    """Fail fast with CredentialError if the Vault secret is incomplete."""
    path = VAULT_PATH_TEMPLATE.format(org_id=org_id)
    secret = vault.read_secret(path)

    missing = [f for f in REQUIRED_FIELDS if not secret.get(f)]
    if missing:
        raise CredentialError(f"Vault secret at {path} is missing required fields: {missing}")

    api_url = secret.get("api_url") or DEFAULT_API_URL
    if not api_url.startswith("https://"):
        raise CredentialError(f"Vault secret at {path}: api_url must start with https://")

    return GitLabAuthConfig(token=secret["token"], group=str(secret["group"]), api_url=api_url)
