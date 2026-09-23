"""
Mock Secrets Vault — in-memory stand-in for Abhiram's Vault module.

Contract it mimics:
    vault.get_secret("azure/service_principal") -> Dict[str, str]
    vault.put_secret(path, value)
    vault.delete_secret(path)
Raises KeyError for missing paths; never stores plaintext in code.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from qa.mocks.mock_azure import VALID_SERVICE_PRINCIPAL


class MockVault:
    def __init__(self, seed: Optional[Dict[str, Dict[str, str]]] = None) -> None:
        self._store: Dict[str, Dict[str, str]] = dict(seed or {})

    def put_secret(self, path: str, value: Dict[str, str]) -> None:
        self._store[path] = dict(value)

    def get_secret(self, path: str) -> Dict[str, str]:
        if path not in self._store:
            raise KeyError(f"secret not found: {path}")
        return dict(self._store[path])

    def delete_secret(self, path: str) -> None:
        self._store.pop(path, None)

    def exists(self, path: str) -> bool:
        return path in self._store


def seeded_vault() -> MockVault:
    """Vault pre-loaded with the standard dev credential paths."""
    return MockVault(
        seed={
            "azure/service_principal": VALID_SERVICE_PRINCIPAL,
            "splunk/hec": {"token": "team-splunk-token"},
            "dummy/api_key": {"api_key": "dummy-key-123"},
        }
    )
