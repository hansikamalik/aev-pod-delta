import pytest
from unittest.mock import patch, MagicMock
from vault_audit.client import VaultClient, VaultAuthError


def test_get_connector_credentials_success():
    """Verifies successfully fetching isolated secrets from Vault KV v2 engine path."""
    vault_url = "https://vault.internal:8200"
    token = "test-token-123"
    namespace = "ns-soc"

    with patch("requests.Session") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        # Mock Vault HTTP JSON Response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "data": {
                "data": {
                    "api_key": "secret-api-key",
                    "host": "https://splunk.internal:8089"
                }
            }
        }
        mock_session.get.return_value = mock_response

        vault_client = VaultClient(vault_url=vault_url, token=token, namespace=namespace)
        creds = vault_client.get_connector_credentials("splunk_prod")

        # Assert isolated vault path structure
        expected_url = "https://vault.internal:8200/v1/secret/data/connectors/splunk_prod/config"
        mock_session.get.assert_called_once_with(expected_url, timeout=10)

        # Assert returned secret dictionary matches
        assert creds["api_key"] == "secret-api-key"
        assert creds["host"] == "https://splunk.internal:8089"


def test_get_connector_credentials_auth_failure():
    """Verifies VaultAuthError is raised when Vault returns 403 / 404 error response."""
    with patch("requests.Session") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("403 Forbidden")
        mock_session.get.return_value = mock_response

        vault_client = VaultClient(vault_url="https://vault.internal:8200", token="invalid-token")

        with pytest.raises(VaultAuthError) as exc_info:
            vault_client.get_connector_credentials("splunk_prod")

        assert "Failed to isolate and load credentials for connector 'splunk_prod'" in str(exc_info.value)
