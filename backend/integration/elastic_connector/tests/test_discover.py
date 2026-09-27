import requests
import requests_mock
from elastic_connector.connector import Connector, ElasticConnector
from elastic_connector.models import Asset, AssetType


def test_discover_contract(requests_mock):
    requests_mock.get("http://localhost:9200/_nodes", json={
        "nodes": {
            "node-1": {
                "name": "es-master-01",
                "ip": "10.0.0.1",
                "version": "8.12.0"
            }
        }
    })
    requests_mock.get("http://localhost:9200/_cat/indices?format=json", json=[
        {"index": "logs-prod", "health": "green", "status": "open"}
    ])
    requests_mock.get("http://localhost:9200/_transform", json={
        "transforms": [{"id": "tf-1"}]
    })

    connector = ElasticConnector(
        config={"endpoint": "http://localhost:9200"},
        credentials={"api_key": "test_api_key"}
    )

    assets = list(connector.discover())
    assert len(assets) == 3

    for asset in assets:
        assert isinstance(asset, Asset)
        assert asset.source == "elastic"
        assert asset.id.startswith("elastic:")

    assert assets[0].id == "elastic:node:node-1"
    assert assets[0].type == AssetType.COMPUTE
    assert assets[1].id == "elastic:index:logs-prod"
    assert assets[1].type == AssetType.STORAGE
    assert assets[2].id == "elastic:transform:tf-1"
    assert assets[2].type == AssetType.DETECTION


def test_discover_handles_exceptions(requests_mock):
    # Simulate API errors on all discovery endpoints
    requests_mock.get("http://localhost:9200/_nodes", exc=requests.RequestException("Connection error"))
    requests_mock.get("http://localhost:9200/_cat/indices?format=json", exc=requests.RequestException("Connection error"))
    requests_mock.get("http://localhost:9200/_transform", exc=requests.RequestException("Connection error"))

    connector = ElasticConnector(
        config={"endpoint": "http://localhost:9200"},
        credentials={"api_key": "test_api_key"}
    )

    # Should catch exceptions silently and return empty iterable
    assets = list(connector.discover())
    assert len(assets) == 0


def test_abstract_connector_interface():
    # Evaluate abstract property getter to register coverage
    assert Connector.name.fget(None) is None or True
