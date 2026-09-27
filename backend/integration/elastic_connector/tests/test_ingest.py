from unittest.mock import MagicMock
from elastic_connector.connector import ElasticConnector
from elastic_connector.models import Asset, AssetType


def test_ingest_pushes_assets():
    mock_platform = MagicMock()
    connector = ElasticConnector(
        config={"endpoint": "http://localhost:9200"},
        credentials={"api_key": "dummy"},
        platform_client=mock_platform
    )

    test_assets = [
        Asset(
            id="elastic:index:test",
            source="elastic",
            type=AssetType.STORAGE,
            name="test",
            raw={}
        )
    ]

    pushed_count = connector.ingest(test_assets)

    assert pushed_count == 1
    mock_platform.bulk_upsert.assert_called_once_with(test_assets)


def test_ingest_without_platform_client():
    connector = ElasticConnector(
        config={"endpoint": "http://localhost:9200"},
        credentials={"api_key": "dummy"},
        platform_client=None
    )

    test_assets = [
        Asset(
            id="elastic:index:test",
            source="elastic",
            type=AssetType.STORAGE,
            name="test",
            raw={}
        )
    ]

    pushed_count = connector.ingest(test_assets)
    assert pushed_count == 1


def test_describe_schemas():
    connector = ElasticConnector(
        config={"endpoint": "http://localhost:9200"},
        credentials={"api_key": "dummy"}
    )

    config_schema = connector.describe_config()
    cred_schema = connector.describe_credentials()

    assert "properties" in config_schema
    assert "properties" in cred_schema
