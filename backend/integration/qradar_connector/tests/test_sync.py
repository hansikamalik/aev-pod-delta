import pytest
from unittest.mock import patch
from qradar_connector.connector import QRadarConnector

@pytest.mark.anyio
async def test_sync_success():
    """Uses anyio (pre-installed in your environment) to run the async test."""
    connector = QRadarConnector({"host": "qradar.local"}, {"sec_token": "token"})
    mock_raw = [{"id": 5, "host_names": [{"name": "db-server"}]}]

    with patch.object(connector.client, "list_assets", return_value=mock_raw):
        with patch.object(connector.platform_client, "bulk_upsert", return_value=1):
            result = await connector.sync()

            assert result.connector == "qradar"
            assert result.status == "success"
            assert result.assets_discovered == 1
            assert result.assets_pushed == 1
            assert len(result.errors) == 0
