"""Credential retrieval through HashiCorp Vault (KV v2)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import requests


class VaultError(Exception):
    """Raised when a Vault lookup fails."""


@dataclass
class VaultCredentials:
    username: Optional[str] = None
    password: Optional[str] = None
    oauth_client_id: Optional[str] = None
    oauth_client_secret: Optional[str] = None


def _split_kv2_path(path: str) -> tuple:
    """'secret/data/connectors/servicenow' -> ('secret', 'connectors/servicenow')."""
    parts = path.strip("/").split("/", 2)
    if len(parts) < 3 or parts[1] != "data":
        raise VaultError(
            f"path {path!r} is not a KV v2 path; expected '<mount>/data/<key>'"
        )
    return parts[0], parts[2]


class VaultClient:
    """Minimal Vault KV v2 client (token auth)."""

    def __init__(
        self,
        addr: Optional[str] = None,
        token: Optional[str] = None,
        namespace: Optional[str] = None,
        timeout: int = 10,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.addr = (addr or os.environ.get("VAULT_ADDR", "")).rstrip("/")
        self.token = token or os.environ.get("VAULT_TOKEN", "")
        self.namespace = namespace or os.environ.get("VAULT_NAMESPACE")
        self.timeout = timeout
        self.session = session or requests.Session()
        if not self.addr:
            raise VaultError("VAULT_ADDR is not set")
        if not self.token:
            raise VaultError("VAULT_TOKEN is not set")

    def read_secret(self, path: str) -> dict:
        mount, key = _split_kv2_path(path)
        url = f"{self.addr}/v1/{mount}/data/{key}"
        headers = {"X-Vault-Token": self.token}
        if self.namespace:
            headers["X-Vault-Namespace"] = self.namespace
        resp = self.session.get(url, headers=headers, timeout=self.timeout)
        if resp.status_code == 404:
            raise VaultError(f"no secret found at {path}")
        if resp.status_code != 200:
            raise VaultError(f"vault read failed: {resp.status_code} {resp.text[:200]}")
        return resp.json().get("data", {}).get("data", {})

    def read_connector_credentials(self, cfg: dict) -> VaultCredentials:
        """Map a connector config's vault section to VaultCredentials."""
        secret = self.read_secret(cfg["path"])
        return VaultCredentials(
            username=secret.get(cfg.get("username_key", "username")),
            password=secret.get(cfg.get("password_key", "password")),
            oauth_client_id=secret.get(cfg.get("client_id_key", "oauth_client_id")),
            oauth_client_secret=secret.get(cfg.get("client_secret_key", "oauth_client_secret")),
        )
