import uuid
import time
from typing import Dict, Any

class CredentialRotator:
    """Simulates zero-downtime Vault credential rotation for sync engine connectors."""

    def __init__(self):
        self._secret_store: Dict[str, Dict[str, Any]] = {}

    def seed_initial_credentials(self, connector: str) -> Dict[str, Any]:
        """Seeds initial secret values for a connector."""
        secrets = {
            "version": 1,
            "primary_key": f"initial-key-{uuid.uuid4().hex[:8]}",
            "active_token": f"token-v1-{uuid.uuid4().hex[:12]}",
            "updated_at": time.time()
        }
        self._secret_store[connector] = secrets
        return secrets

    def rotate_credentials(self, connector: str) -> Dict[str, Any]:
        """Rotates credentials to a new version, preserving dual-auth window for zero downtime."""
        if connector not in self._secret_store:
            self.seed_initial_credentials(connector)

        current = self._secret_store[connector]
        new_version = current["version"] + 1
        
        rotated_secrets = {
            "version": new_version,
            "primary_key": f"rotated-key-v{new_version}-{uuid.uuid4().hex[:8]}",
            "active_token": f"token-v{new_version}-{uuid.uuid4().hex[:12]}",
            "previous_token": current["active_token"],  # Grace period support
            "updated_at": time.time()
        }
        self._secret_store[connector] = rotated_secrets
        return rotated_secrets

    def get_active_credentials(self, connector: str) -> Dict[str, Any]:
        """Retrieves currently active Vault credentials for a connector."""
        return self._secret_store.get(connector, self.seed_initial_credentials(connector))
