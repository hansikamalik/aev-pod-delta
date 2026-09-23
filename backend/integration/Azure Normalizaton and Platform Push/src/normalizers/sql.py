from typing import Dict, Any
from .base import AzureBaseNormalizer


class SQLNormalizer(AzureBaseNormalizer):
    """Normalizes Microsoft.Sql/servers/databases ARM objects."""

    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        metadata = self.extract_common_metadata(raw_data)
        properties = raw_data.get("properties", {})
        sku = raw_data.get("sku", {})

        return {
            "asset_id": metadata["asset_id"],
            "name": metadata["name"],
            "cloud_provider": "azure",
            "resource_type": "database",
            "native_type": "Microsoft.Sql/servers/databases",
            "region": metadata["region"],
            "subscription_id": metadata["subscription_id"],
            "resource_group": metadata["resource_group"],
            "tags": metadata["tags"],
            "normalized_at": metadata["normalized_at"],
            "attributes": {
                "edition": sku.get("tier") or properties.get("edition"),
                "sku_name": sku.get("name"),
                "max_size_bytes": properties.get("maxSizeBytes"),
                "status": properties.get("status"),
                "collation": properties.get("collation"),
                "earliest_restore_date": properties.get("earliestRestoreDate")
            }
        }
