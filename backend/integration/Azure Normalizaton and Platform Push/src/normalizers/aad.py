from typing import Dict, Any
from datetime import datetime, timezone
from .base import AzureBaseNormalizer


class AADNormalizer(AzureBaseNormalizer):
    """Normalizes Microsoft Graph API User/Group identity objects."""

    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        object_id = raw_data.get("id", "")
        upn = raw_data.get("userPrincipalName")
        
        # Determine Graph type (User vs Group)
        is_user = "userPrincipalName" in raw_data or raw_data.get("userType") is not None
        native_type = "Microsoft.Graph/users" if is_user else "Microsoft.Graph/groups"

        return {
            "asset_id": f"azure:aad:{object_id}" if not object_id.startswith("azure:aad:") else object_id,
            "name": upn or raw_data.get("displayName", "unknown"),
            "cloud_provider": "azure",
            "resource_type": "identity",
            "native_type": native_type,
            "region": "global",
            "subscription_id": None,
            "resource_group": None,
            "tags": {},
            "normalized_at": datetime.now(timezone.utc).isoformat(),
            "attributes": {
                "object_id": object_id,
                "user_principal_name": upn,
                "display_name": raw_data.get("displayName"),
                "account_enabled": raw_data.get("accountEnabled", True),
                "user_type": raw_data.get("userType", "Member"),
                "assigned_roles": raw_data.get("assignedRoles", [])
            }
        }
