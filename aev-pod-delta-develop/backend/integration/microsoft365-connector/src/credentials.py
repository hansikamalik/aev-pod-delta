"""
Vault credential retrieval.

Wraps HashiCorp Vault's KV v2 HTTP API. Point `addr` (and VAULT_TOKEN, read
from the environment — never hardcode it) at the squad's real Vault
instance; the path convention here is a placeholder.
"""

import os
from typing import Any, Dict, Optional

import requests

from .exceptions import VaultError


class VaultClient:
    def __init__(self, addr: str, token: Optional[str] = None, timeout: float = 5.0):
        self.addr = addr.rstrip("/")
        self.token = token or os.environ.get("VAULT_TOKEN")
        self.timeout = timeout
        if not self.token:
            raise VaultError(
                "No Vault token available. Set VAULT_TOKEN in the environment."
            )

    def get_secret(self, path: str) -> Dict[str, Any]:
        """
        Fetch a KV v2 secret. `path` should look like
        'secret/data/aev/connectors/microsoft365/azure_ad'.
        """
        url = f"{self.addr}/v1/{path}"
        try:
            resp = requests.get(
                url,
                headers={"X-Vault-Token": self.token},
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise VaultError(f"Failed to read secret at {path}: {exc}") from exc

        body = resp.json()
        try:
            return body["data"]["data"]
        except (KeyError, TypeError) as exc:
            raise VaultError(f"Unexpected Vault response shape for {path}") from exc
