from unittest.mock import patch
import pytest
import requests_mock
from elastic_connector.connector import ElasticConnector


@pytest.mark.asyncio
async def test_sync_success(requests_mock):
    requests_mock.get("http://localhost:9200/_nodes", json={"nodes": {}})
    requests_mock.get("http://localhost:9200/_cat/indices?format=json", json=[])
    requests_mock.get("http://localhost:9200/_transform", json={"transforms": []})

    connector = ElasticConnector(
        config={"endpoint": "http://localhost:9200"},
        credentials={"api_key": "test"}
    )

    result = await connector.sync()

    assert result.connector == "elastic"
    assert result.status == "success"
    assert result.assets_discovered == 0
    assert result.assets_pushed == 0
    assert result.errors == []


@pytest.mark.asyncio
async def test_sync_failure():
    connector = ElasticConnector(
        config={"endpoint": "http://localhost:9200"},
        credentials={"api_key": "test"}
    )

    # Force discover() to raise an unhandled error to test sync error logging
    with patch.object(connector, "discover", side_effect=RuntimeError("Cluster unavailable")):
        result = await connector.sync()

    assert result.connector == "elastic"
    assert result.status == "failed"
    assert result.assets_discovered == 0
    assert result.assets_pushed == 0
    assert len(result.errors) == 1
    assert result.errors[0]["message"] == "Cluster unavailable"
