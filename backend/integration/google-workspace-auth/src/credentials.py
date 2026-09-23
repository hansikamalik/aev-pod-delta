"""
Credential retrieval, wired through Vault.

Est: 0.5 day (per plan's per-connector standard pattern)

TODO(Bhawook): Swap `VaultClientProtocol` / `MockVaultClient` for the
real internal Vault client (same swap as the SentinelOne connector). The
connector only depends on `.read_secret(path)`.
"""

import json
from typing import Dict, List, Optional, Protocol

from .auth import GoogleWorkspaceAuthConfig

VAULT_PATH_TEMPLATE = "secret/connectors/google-workspace/{org_id}"

# Top-level fields the Vault secret must have. service_account_json is
# itself a JSON-encoded string (Vault secrets are string key/value), parsed
# and validated separately below.
REQUIRED_FIELDS = ["service_account_json", "delegated_admin_email"]
REQUIRED_SA_FIELDS = ["client_email", "private_key", "token_uri"]

# OAuth scopes requested for the impersonated session, used when the Vault
# secret doesn't include its own "scopes" field. Per FR-INT-012 (user
# inventory; audit log) — Week 2's discover()/ingest() work may need to
# extend this list.
DEFAULT_SCOPES: List[str] = [
    "https://www.googleapis.com/auth/admin.directory.user.readonly",
    "https://www.googleapis.com/auth/admin.reports.audit.readonly",
]


class VaultClientProtocol(Protocol):
    def read_secret(self, path: str) -> Dict[str, str]:
        ...


class MockVaultClient:
    """Local stand-in for the real Vault client, used only for tests/dev."""

    def __init__(self, fixtures: Optional[Dict[str, Dict[str, str]]] = None):
        self._fixtures = fixtures or {}

    def read_secret(self, path: str) -> Dict[str, str]:
        if path not in self._fixtures:
            raise KeyError(f"No secret at Vault path: {path}")
        return self._fixtures[path]


class CredentialError(Exception):
    pass


def _parse_scopes(raw_scopes: Optional[str]) -> List[str]:
    """
    Vault secrets are string key/value, so a "scopes" override may arrive as
    a JSON-encoded list ('["https://...", "https://..."]') or, if someone
    hand-wrote the secret, a single scope string. Fall back to DEFAULT_SCOPES
    if the field is absent.
    """
    if not raw_scopes:
        return list(DEFAULT_SCOPES)
    try:
        parsed = json.loads(raw_scopes)
        return list(parsed) if isinstance(parsed, list) else [str(parsed)]
    except (TypeError, json.JSONDecodeError):
        return [raw_scopes]


def load_google_workspace_credentials(
    vault: VaultClientProtocol, org_id: str
) -> GoogleWorkspaceAuthConfig:
    """Fail fast with CredentialError if the Vault secret is incomplete or malformed."""
    path = VAULT_PATH_TEMPLATE.format(org_id=org_id)
    secret = vault.read_secret(path)

    missing = [f for f in REQUIRED_FIELDS if not secret.get(f)]
    if missing:
        raise CredentialError(f"Vault secret at {path} is missing required fields: {missing}")

    raw_sa = secret["service_account_json"]
    try:
        service_account_info = json.loads(raw_sa)
    except (TypeError, json.JSONDecodeError) as exc:
        raise CredentialError(
            f"Vault secret at {path}: service_account_json is not valid JSON"
        ) from exc

    missing_sa_fields = [f for f in REQUIRED_SA_FIELDS if f not in service_account_info]
    if missing_sa_fields:
        raise CredentialError(
            f"Vault secret at {path}: service_account_json is missing "
            f"required field(s): {missing_sa_fields}"
        )

    return GoogleWorkspaceAuthConfig(
        service_account_info=service_account_info,
        delegated_admin_email=secret["delegated_admin_email"],
        scopes=_parse_scopes(secret.get("scopes")),
        org_id=org_id,
    )
