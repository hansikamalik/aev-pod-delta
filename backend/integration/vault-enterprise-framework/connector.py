from datetime import datetime
from typing import Iterable, Dict, Any, Optional

from sdk.connector import Connector
from sdk.models import Asset, AssetType
from .client import VaultEnterpriseClient


class VaultEnterpriseConnector(Connector):
    name: str = "vault-enterprise"

    def __init__(
        self,
        config: Dict[str, Any],
        credentials: Dict[str, Any],
        platform_client: Optional[Any] = None,
    ):
        self.config = config
        self.credentials = credentials
        self._platform_client = platform_client

        self.client = VaultEnterpriseClient(
            vault_addr=self.config.get("vault_addr", ""),
            namespace=self.config.get("namespace", "root"),
            token=self.credentials.get("vault_token"),
            verify_tls=self.config.get("verify_tls", True),
        )

    def check_health(self) -> bool:
        try:
            return self.client.ping()
        except Exception:
            return False

    def describe_config(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "vault_addr": {"type": "string", "format": "uri"},
                "namespace": {"type": "string", "default": "root"},
                "verify_tls": {"type": "boolean", "default": True},
            },
            "required": ["vault_addr"],
        }

    def describe_credentials(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "vault_token": {"type": "string", "secret": True},
            },
            "required": ["vault_token"],
        }

    def discover(self) -> Iterable[Asset]:
        # 1. Discover Enterprise Namespaces -> AssetType.IDENTITY
        for ns in self.client.list_namespaces():
            yield Asset(
                id=f"{self.name}:namespace:{ns['id']}",
                source=self.name,
                type=AssetType.IDENTITY.value,
                name=f"Namespace: {ns['path']}",
                raw=ns,
                discoveredAt=datetime.utcnow(),
            )

        # 2. Discover Secrets Engines -> AssetType.STORAGE
        for mount_path, mount_info in self.client.list_secret_engines().items():
            yield Asset(
                id=f"{self.name}:mount:{mount_path.strip('/')}",
                source=self.name,
                type=AssetType.STORAGE.value,
                name=f"Secret Engine: {mount_path}",
                raw=mount_info,
                discoveredAt=datetime.utcnow(),
            )

    def ingest(self, assets: Iterable[Asset]) -> int:
        asset_list = list(assets)
        if not asset_list:
            return 0

        if self._platform_client:
            self._platform_client.bulk_upsert(asset_list)

        return len(asset_list)
