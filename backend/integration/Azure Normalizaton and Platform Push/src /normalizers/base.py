
import abc
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from src.interfaces.base_normalizer import BaseNormalizer


class AzureBaseNormalizer(BaseNormalizer):
    """Base class implementing shared metadata extraction for Azure resources."""

    def extract_common_metadata(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        resource_id = raw_data.get("id", "")
        
        # Parse Resource Group from ARM ID
        resource_group = None
        if "/resourceGroups/" in resource_id:
            parts = resource_id.split("/")
            try:
                rg_idx = parts.index("resourceGroups") + 1
                resource_group = parts[rg_idx]
            except (ValueError, IndexError):
                pass

        # Parse Subscription ID from ARM ID if not explicitly set
        sub_id = self.subscription_id
        if not sub_id and "/subscriptions/" in resource_id:
            parts = resource_id.split("/")
            try:
                sub_idx = parts.index("subscriptions") + 1
                sub_id = parts[sub_idx]
            except (ValueError, IndexError):
                pass

        # Normalization location handling
        region = raw_data.get("location", "global")
        region = region.lower() if region else "global"

        return {
            "asset_id": resource_id,
            "name": raw_data.get("name", "unknown"),
            "region": region,
            "subscription_id": sub_id,
            "resource_group": resource_group,
            "tags": raw_data.get("tags") or {},
            "normalized_at": datetime.now(timezone.utc).isoformat()
        }
