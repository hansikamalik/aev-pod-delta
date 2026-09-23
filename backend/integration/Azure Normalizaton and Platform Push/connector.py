from datetime import datetime
from typing import Iterable, Dict, Any, Optional
import logging

from sdk.connector import Connector
from sdk.models import Asset, AssetType

logger = logging.getLogger(__name__)


class AzureConnector(Connector):
    name: str = "azure"

    def __init__(
        self,
        config: Dict[str, Any],
        credentials: Dict[str, Any],
        platform_client: Optional[Any] = None,
    ):
        self.config = config
        self.credentials = credentials
        self._platform_client = platform_client
        self.subscription_id = self.config.get("subscription_id")

    def check_health(self) -> bool:
        return bool(self.subscription_id)

    def describe_config(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "subscription_id": {"type": "string"},
            },
            "required": ["subscription_id"],
        }

    def describe_credentials(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "secret": True},
                "client_secret": {"type": "string", "secret": True},
                "tenant_id": {"type": "string", "secret": True},
            },
            "required": ["client_id", "client_secret", "tenant_id"],
        }

    def _map_azure_type(self, azure_type: str) -> str:
        t = azure_type.lower()
        if "compute/virtualmachines" in t:
            return AssetType.COMPUTE.value
        elif "storage/storageaccounts" in t:
            return AssetType.STORAGE.value
        elif "network/" in t:
            return AssetType.NETWORK.value
        elif "keyvault/vaults" in t or "authorization/" in t:
            return AssetType.IDENTITY.value
        return AssetType.OTHER.value

    def discover(self) -> Iterable[Asset]:
        raw_resources = [
            {
                "id": f"/subscriptions/{self.subscription_id}/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm-01",
                "name": "vm-01",
                "type": "Microsoft.Compute/virtualMachines",
                "tags": {"env": "prod"},
            },
            {
                "id": f"/subscriptions/{self.subscription_id}/resourceGroups/rg1/providers/Microsoft.Storage/storageAccounts/st01",
                "name": "st01",
                "type": "Microsoft.Storage/storageAccounts",
                "tags": {"tier": "hot"},
            },
        ]

        for res in raw_resources:
            yield Asset(
                id=res["id"],
                source=self.name,
                type=self._map_azure_type(res["type"]),
                name=res["name"],
                raw=res,
                discoveredAt=datetime.utcnow(),
                tags=res.get("tags", {}),
            )

    def ingest(self, assets: Iterable[Asset]) -> int:
        asset_list = list(assets)
        if not asset_list:
            return 0

        if self._platform_client:
            self._platform_client.bulk_upsert(asset_list)

        return len(asset_list)
