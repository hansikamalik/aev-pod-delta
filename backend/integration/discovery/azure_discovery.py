from typing import Any, Dict, List

from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.sql import SqlManagementClient
from azure.mgmt.web import WebSiteManagementClient

from backend.integration.auth.azure_auth import AzureServicePrincipalAuthenticator

# AAD discovery is pending Connector SDK/platform agreement.
# Resource types, client/SDK, endpoints, permissions, and final contract
# are not yet specified.
#
# PROVISIONAL — INFORM SDK SQUAD.


class AzureDiscovery:
    """
    Azure resource discovery helper for ARM-based Azure resources.

    PROVISIONAL — INFORM SDK SQUAD:
    - internal discovery method signatures
    - raw resource representation
    - Azure SDK dependency versions
    - subscription handling
    """

    def __init__(self, authenticator: AzureServicePrincipalAuthenticator, subscription_ids: List[str]):
        if not subscription_ids:
            raise ValueError("Explicit subscription IDs are required for discovery.")
        self.authenticator = authenticator
        self.subscription_ids = subscription_ids
        self.credential = authenticator.get_credential()

    def discover_virtual_machines(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for subscription_id in self.subscription_ids:
            client = ComputeManagementClient(self.credential, subscription_id)
            for vm in client.virtual_machines.list_all():
                results.append(
                    self._normalize_arm_resource(
                        vm,
                        subscription_id,
                        resource_type="virtual_machine",
                    )
                )
        return results

    def discover_storage_accounts(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for subscription_id in self.subscription_ids:
            client = StorageManagementClient(self.credential, subscription_id)
            for account in client.storage_accounts.list():
                results.append(
                    self._normalize_arm_resource(
                        account,
                        subscription_id,
                        resource_type="storage_account",
                    )
                )
        return results

    def discover_sql_servers(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for subscription_id in self.subscription_ids:
            client = SqlManagementClient(self.credential, subscription_id)
            for server in client.servers.list():
                results.append(
                    self._normalize_arm_resource(
                        server,
                        subscription_id,
                        resource_type="sql_server",
                    )
                )
        return results

    def discover_function_apps(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for subscription_id in self.subscription_ids:
            client = WebSiteManagementClient(self.credential, subscription_id)
            for function_app in client.web_apps.list():
                results.append(
                    self._normalize_arm_resource(
                        function_app,
                        subscription_id,
                        resource_type="function_app",
                    )
                )
        return results

    def _normalize_arm_resource(
        self,
        resource: Any,
        subscription_id: str,
        resource_type: str,
    ) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {
            "resource_type": resource_type,
            "subscription_id": subscription_id,
            "id": getattr(resource, "id", None),
            "name": getattr(resource, "name", None),
            "type": getattr(resource, "type", None),
            "location": getattr(resource, "location", None),
            "raw": resource if not hasattr(resource, "as_dict") else resource.as_dict(),
        }
        return normalized