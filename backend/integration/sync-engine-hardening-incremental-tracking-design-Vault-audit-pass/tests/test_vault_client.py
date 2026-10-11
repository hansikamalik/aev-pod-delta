import pytest
from unittest.mock import patch, MagicMock


from vault_audit.client import VaultClient


def test_get_connector_credentials_success():
    vault_url = "https://vault.internal:8200"
    token = "test-token-123"

    with patch("requests.Session") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

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

        vault_client = VaultClient(vault_url=vault_url, token=token)
        creds = vault_client.get_connector_credentials("splunk_prod")

        expected_url = "https://vault.internal:8200/v1/secret/data/connectors/splunk_prod/config"
        mock_session.get.assert_called_once_with(expected_url, timeout=10)
        assert creds["api_key"] == "secret-api-key"
