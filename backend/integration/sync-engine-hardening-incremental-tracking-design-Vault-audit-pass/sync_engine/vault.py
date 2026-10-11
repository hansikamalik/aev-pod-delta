import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class VaultClient:
    """Vault Enterprise client interface for credential management & secret audit pass."""

    def __init__(self, vault_addr: str = "http://127.0.0.1:8200", token: str = "root_token"):
        self.vault_addr = vault_addr
        self.token = token
        self._store: Dict[str, Dict[str, Any]] = {
            "splunk_connector": {"api_key": "splk_secret_9988", "url": "https://splunk.internal:8089"},
            "elastic_connector": {"api_key": "elk_sec_1122", "url": "https://elastic.internal:9200"},
            "cyberark_auth_module": {"client_secret": "cybr_sec_3344", "app_id": "CyberArk_Prod"},
            "cyberark-discovery-integration": {"api_token": "cybr_disc_5566", "endpoint": "https://cyberark.internal/api"},
            "vault-enterprise-framework": {"role_id": "vlt_role_7788", "secret_id": "vlt_sec_9900"},
            "qradar_connector": {"sec_token": "qradar_sec_4455", "console_url": "https://qradar.internal"},
            "Azure_Normalization_Platform_Push": {"tenant_id": "az_tenant_11", "client_secret": "az_sec_8899"},
        }

    def get_connector_credentials(self, connector_id: str) -> Dict[str, Any]:
        if connector_id not in self._store:
            raise KeyError(f"No credentials registered in Vault for connector: {connector_id}")
        logger.info("Retrieved Vault credentials for %s", connector_id)
        return self._store[connector_id]
