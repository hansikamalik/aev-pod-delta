from typing import Iterable, Dict, Any
from connector_sdk import Connector, Asset, AssetType, SyncResult

class DogfoodSampleConnector(Connector):
    name = "dogfood_sample"

    def check_health(self) -> bool:
        # SDK contract: returns boolean for quick health checks[cite: 2]
        return True

    def discover(self) -> Iterable[Asset]:
        # SDK contract: reads mock records and returns normalized Asset objects[cite: 2]
        yield Asset(
            id="dogfood-asset-001",
            source=self.name,
            type=AssetType.OTHER,
            name="Dogfood Test Entity",
            raw={"id": "dogfood-asset-001", "status": "active"},
            tags={"environment": "sandbox"}
        )

    def ingest(self, assets: Iterable[Asset]) -> int:
        # SDK contract: pushes assets and returns count[cite: 2]
        asset_list = list(assets)
        return len(asset_list)

    def describe_config(self) -> Dict[str, Any]:
        # SDK contract: describes non-secret settings[cite: 2]
        return {
            "type": "object",
            "properties": {
                "environment": {"type": "string", "description": "Target environment"}
            },
            "required": ["environment"]
        }

    def describe_credentials(self) -> Dict[str, Any]:
        # SDK contract: describes credentials with secret flags[cite: 2]
        return {
            "type": "object",
            "properties": {
                "api_key": {"type": "string", "secret": True, "description": "Sandbox API key"}
            },
            "required": ["api_key"]
        }
