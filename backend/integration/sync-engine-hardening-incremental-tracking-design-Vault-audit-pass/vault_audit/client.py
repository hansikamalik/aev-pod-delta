from typing import Any, Dict, Optional
import requests


class VaultAuthError(Exception):
    """Raised when authentication or fetching secrets from HashiCorp Vault fails."""
    pass


class VaultClient:
    def __init__(self, vault_url: str, token: str, namespace: Optional[str] = None):
        self.vault_url = vault_url.rstrip("/")
        self.token = token
        self.namespace = namespace
        self.session = requests.Session()
        self.session.headers.update({"X-Vault-Token": self.token})
        if self.namespace:
            self.session.headers.update({"X-Vault-Namespace": self.namespace})

    def get_connector_credentials(self, connector_id: str) -> Dict[str, Any]:
        """
        Enforces isolation path: /v1/secret/data/connectors/{connector_id}/config
        """
        path = f"{self.vault_url}/v1/secret/data/connectors/{connector_id}/config"
        try:
            response = self.session.get(path, timeout=10)
            response.raise_for_status()
            payload = response.json()
            return payload.get("data", {}).get("data", {})
        except Exception:
            raise VaultAuthError(f"Failed to isolate and load credentials for connector '{connector_id}'") from None
