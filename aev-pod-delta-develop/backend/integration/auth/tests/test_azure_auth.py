from unittest.mock import patch

import pytest

from backend.integration.auth.azure_auth import AzureServicePrincipalAuthenticator


def test_builds_client_secret_credential_from_generic_input():
    auth_data = {
        "client_id": "client-123",
        "client_secret": "secret-abc",
    }
    tenant_id = "tenant-xyz"
    subscription_ids = ["sub-1", "sub-2"]

    with patch(
        "backend.integration.auth.azure_auth.ClientSecretCredential"
    ) as mock_credential:
        mock_credential.return_value = object()

        auth = AzureServicePrincipalAuthenticator(
            auth_data=auth_data,
            tenant_id=tenant_id,
            subscription_ids=subscription_ids,
        )

        credential = auth.get_credential()

        mock_credential.assert_called_once_with(
            tenant_id=tenant_id,
            client_id="client-123",
            client_secret="secret-abc",
        )

        assert credential is mock_credential.return_value
        assert auth.get_subscription_ids() == subscription_ids


def test_rejects_missing_client_id():
    auth_data = {"client_secret": "secret-abc"}

    auth = AzureServicePrincipalAuthenticator(
        auth_data=auth_data,
        tenant_id="tenant-xyz",
    )

    with pytest.raises(
        ValueError,
        match="Missing Service Principal client_id",
    ):
        auth.get_credential()


def test_rejects_missing_client_secret():
    auth_data = {"client_id": "client-123"}

    auth = AzureServicePrincipalAuthenticator(
        auth_data=auth_data,
        tenant_id="tenant-xyz",
    )

    with pytest.raises(
        ValueError,
        match="Missing Service Principal client_secret",
    ):
        auth.get_credential()


def test_rejects_missing_tenant_id():
    auth_data = {
        "client_id": "client-123",
        "client_secret": "secret-abc",
    }

    auth = AzureServicePrincipalAuthenticator(
        auth_data=auth_data,
        tenant_id="",
    )

    with pytest.raises(
        ValueError,
        match="Missing tenant_id",
    ):
        auth.get_credential()