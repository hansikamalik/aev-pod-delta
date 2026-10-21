import uuid
from typing import Dict, Any


class VaultClient:
    """Simulates HashiCorp Vault credential retrieval and zero-hardcoding verification."""

    def __init__(self):
        self._store = {}

    def get_credentials(self, connector_id: str) -> Dict[str, Any]:
        if connector_id not in self._store:
            self._store[connector_id] = {
                "version": 1,
                "active_token": f"vault_token_{uuid.uuid4().hex[:12]}"
            }
        return self._store[connector_id]

    def rotate_credentials(self, connector_id: str) -> Dict[str, Any]:
        current = self.get_credentials(connector_id)
        new_version = current["version"] + 1
        new_token = f"vault_token_{uuid.uuid4().hex[:12]}"
        self._store[connector_id] = {"version": new_version, "active_token": new_token}
        return self._store[connector_id]
