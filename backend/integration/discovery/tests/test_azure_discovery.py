from unittest.mock import MagicMock, patch

import pytest

from backend.integration.auth.azure_auth import AzureServicePrincipalAuthenticator
from backend.integration.discovery.azure_discovery import AzureDiscovery


def make_authenticator():
    auth_data = {"client_id": "client-123", "client_secret": "secret-abc"}
    return AzureServicePrincipalAuthenticator(auth_data=auth_data, tenant_id="tenant-xyz")


def test_missing_subscription_ids_raises():
    authenticator = make_authenticator()

    with pytest.raises(ValueError, match="Explicit subscription IDs are required for discovery"):
        AzureDiscovery(authenticator=authenticator, subscription_ids=[])


def test_discover_virtual_machines():
    auth_data = {"client_id": "client-123", "client_secret": "secret-abc"}
    subscription_id = "sub-1"

    with patch("backend.integration.auth.azure_auth.ClientSecretCredential") as mock_credential_ctor, patch(
        "backend.integration.discovery.azure_discovery.ComputeManagementClient"
    ) as mock_compute_client:
        mock_credential = object()
        mock_credential_ctor.return_value = mock_credential

        mock_vm = MagicMock()
        mock_vm.id = "vm-id"
        mock_vm.name = "vm-name"
        mock_vm.type = "Microsoft.Compute/virtualMachines"
        mock_vm.location = "eastus"
        mock_compute_client.return_value.virtual_machines.list_all.return_value = [mock_vm]

        authenticator = AzureServicePrincipalAuthenticator(auth_data=auth_data, tenant_id="tenant-xyz")
        discovery = AzureDiscovery(authenticator=authenticator, subscription_ids=[subscription_id])

        results = discovery.discover_virtual_machines()

        mock_compute_client.assert_called_once_with(mock_credential, subscription_id)
        assert results[0]["resource_type"] == "virtual_machine"
        assert results[0]["subscription_id"] == subscription_id
        assert results[0]["id"] == "vm-id"


def test_discover_storage_accounts():
    auth_data = {"client_id": "client-123", "client_secret": "secret-abc"}
    subscription_id = "sub-1"

    with patch("backend.integration.auth.azure_auth.ClientSecretCredential") as mock_credential_ctor, patch(
        "backend.integration.discovery.azure_discovery.StorageManagementClient"
    ) as mock_storage_client:
        mock_credential = object()
        mock_credential_ctor.return_value = mock_credential

        mock_account = MagicMock()
        mock_account.id = "sa-id"
        mock_account.name = "sa-name"
        mock_account.type = "Microsoft.Storage/storageAccounts"
        mock_account.location = "westus"
        mock_storage_client.return_value.storage_accounts.list.return_value = [mock_account]

        authenticator = AzureServicePrincipalAuthenticator(auth_data=auth_data, tenant_id="tenant-xyz")
        discovery = AzureDiscovery(authenticator=authenticator, subscription_ids=[subscription_id])

        results = discovery.discover_storage_accounts()

        mock_storage_client.assert_called_once_with(mock_credential, subscription_id)
        assert results[0]["resource_type"] == "storage_account"
        assert results[0]["id"] == "sa-id"


def test_discover_sql_servers():
    auth_data = {"client_id": "client-123", "client_secret": "secret-abc"}
    subscription_id = "sub-1"

    with patch("backend.integration.auth.azure_auth.ClientSecretCredential") as mock_credential_ctor, patch(
        "backend.integration.discovery.azure_discovery.SqlManagementClient"
    ) as mock_sql_client:
        mock_credential = object()
        mock_credential_ctor.return_value = mock_credential

        mock_server = MagicMock()
        mock_server.id = "sql-id"
        mock_server.name = "sql-name"
        mock_server.type = "Microsoft.Sql/servers"
        mock_server.location = "centralus"
        mock_sql_client.return_value.servers.list.return_value = [mock_server]

        authenticator = AzureServicePrincipalAuthenticator(auth_data=auth_data, tenant_id="tenant-xyz")
        discovery = AzureDiscovery(authenticator=authenticator, subscription_ids=[subscription_id])

        results = discovery.discover_sql_servers()

        mock_sql_client.assert_called_once_with(mock_credential, subscription_id)
        assert results[0]["resource_type"] == "sql_server"
        assert results[0]["id"] == "sql-id"


def test_discover_function_apps():
    auth_data = {"client_id": "client-123", "client_secret": "secret-abc"}
    subscription_id = "sub-1"

    with patch("backend.integration.auth.azure_auth.ClientSecretCredential") as mock_credential_ctor, patch(
        "backend.integration.discovery.azure_discovery.WebSiteManagementClient"
    ) as mock_web_client:
        mock_credential = object()
        mock_credential_ctor.return_value = mock_credential

        mock_function_app = MagicMock()
        mock_function_app.id = "func-id"
        mock_function_app.name = "func-name"
        mock_function_app.type = "Microsoft.Web/sites"
        mock_function_app.location = "eastus2"
        mock_web_client.return_value.web_apps.list.return_value = [mock_function_app]

        authenticator = AzureServicePrincipalAuthenticator(auth_data=auth_data, tenant_id="tenant-xyz")
        discovery = AzureDiscovery(authenticator=authenticator, subscription_ids=[subscription_id])

        results = discovery.discover_function_apps()

        mock_web_client.assert_called_once_with(mock_credential, subscription_id)
        assert results[0]["resource_type"] == "function_app"
        assert results[0]["id"] == "func-id"


def test_discover_multiple_subscriptions():
    auth_data = {"client_id": "client-123", "client_secret": "secret-abc"}
    subscription_ids = ["sub-1", "sub-2"]

    with patch("backend.integration.auth.azure_auth.ClientSecretCredential") as mock_credential_ctor, patch(
        "backend.integration.discovery.azure_discovery.ComputeManagementClient"
    ) as mock_compute_client:
        mock_credential = object()
        mock_credential_ctor.return_value = mock_credential

        mock_vm = MagicMock()
        mock_vm.id = "vm-id"
        mock_vm.name = "vm-name"
        mock_vm.type = "Microsoft.Compute/virtualMachines"
        mock_vm.location = "eastus"
        mock_compute_client.return_value.virtual_machines.list_all.return_value = [mock_vm]

        authenticator = AzureServicePrincipalAuthenticator(auth_data=auth_data, tenant_id="tenant-xyz")
        discovery = AzureDiscovery(authenticator=authenticator, subscription_ids=subscription_ids)

        results = discovery.discover_virtual_machines()

        assert len(results) == 2
        assert results[0]["subscription_id"] == "sub-1"
        assert results[1]["subscription_id"] == "sub-2"
