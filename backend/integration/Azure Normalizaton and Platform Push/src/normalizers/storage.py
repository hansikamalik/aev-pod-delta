from typing import Dict, Any
from .base import AzureBaseNormalizer


class StorageNormalizer(AzureBaseNormalizer):
    """Normalizes Microsoft.Storage/storageAccounts ARM objects."""

    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        metadata = self.extract_common_metadata(raw_data)
        properties = raw_data.get("properties", {})
        sku = raw_data.get("sku", {})
        encryption = properties.get("encryption", {})

        return {
            "asset_id": metadata["asset_id"],
            "name": metadata["name"],
            "cloud_provider": "azure",
            "resource_type": "storage",
            "native_type": "Microsoft.Storage/storageAccounts",
            "region": metadata["region"],
            "subscription_id": metadata["subscription_id"],
            "resource_group": metadata["resource_group"],
            "tags": metadata["tags"],
            "normalized_at": metadata["normalized_at"],
            "attributes": {
                "sku_name": sku.get("name"),
                "sku_tier": sku.get("tier"),
                "access_tier": properties.get("accessTier"),
                "supports_https_only": properties.get("supportsHttpsTrafficOnly", True),
                "encryption_key_source": encryption.get("keySource", "Microsoft.Storage"),
                "provisioning_state": properties.get("provisioningState")
            }
        }
