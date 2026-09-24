import pytest
from unittest.mock import patch, MagicMock
from connector import SplunkConnector


@pytest.mark.anyio
async def test_splunk_incremental_sync_lifecycle():
    mock_platform = MagicMock()
    connector = SplunkConnector(
        config={"host": "splunk.example.com", "search_query": "index=main"},
        credentials={"bearer_token": "secret_token"},
        platform_client=mock_platform
    )

    mock_events = [
        {"_cd": "100:1", "_time": "2026-09-24T10:00:00Z", "_raw": "Security Event 1"},
        {"_cd": "100:2", "_time": "2026-09-24T11:00:00Z", "_raw": "Security Event 2"}
    ]

    with patch.object(connector._client, "ping", return_value=True), \
         patch.object(connector._client, "create_search_job", return_value="sid_12345"), \
         patch.object(connector._client, "get_search_results", return_value=mock_events), \
         patch.object(connector._client, "forward_events", return_value=True):

        result = await connector.sync()

        assert result.status == "success"
        assert result.assets_discovered == 2
        assert result.checkpoint is not None
        assert result.checkpoint.connector == "splunk"
        mock_platform.save_checkpoint.assert_called_once()
