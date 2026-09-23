"""Credential retrieval through HashiCorp Vault.

Priority order for each credential:
1. Vault KV path `secret/connectors/<connector>/<key>`
2. Environment variable `<PREFIX>_<KEY>` (local dev fallback)

Set VAULT_ADDR and VAULT_TOKEN to enable Vault; if hvac is not installed
or Vault is unreachable, the env-var fallback is used transparently.
"""
from __future__ import annotations

import os
from typing import Optional


class CredentialError(RuntimeError):
    pass


def _env_key(prefix: str, key: str) -> str:
    return f"{prefix}_{key}".upper().replace("-", "_")


def get_credential(connector: str, key: str, prefix: Optional[str] = None,
                   required: bool = True) -> Optional[str]:
    prefix = prefix or connector.replace("-", "_")

    # 1) Vault
    addr = os.getenv("VAULT_ADDR")
    token = os.getenv("VAULT_TOKEN")
    if addr and token:
        try:
            import hvac  # optional dependency
            client = hvac.Client(url=addr, token=token)
            if client.is_authenticated():
                resp = client.secrets.kv.v2.read_secret_version(
                    path=f"connectors/{connector}", raise_on_deleted_version=True)
                value = resp["data"]["data"].get(key)
                if value:
                    return value
        except Exception:
            pass  # fall through to env vars

    # 2) Env fallback
    value = os.getenv(_env_key(prefix, key))
    if value:
        return value

    if required:
        raise CredentialError(
            f"Missing credential '{key}' for connector '{connector}'. "
            f"Set Vault path secret/connectors/{connector} or env {_env_key(prefix, key)}.")
    return None
