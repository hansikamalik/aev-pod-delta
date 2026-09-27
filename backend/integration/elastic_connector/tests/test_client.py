import pytest
import requests
import requests_mock
from elastic_connector.client import ElasticClient


def test_client_retry_and_succeed(requests_mock):
    requests_mock.get("http://localhost:9200/_nodes", [
        {"status_code": 503},
        {"status_code": 503},
        {"json": {"nodes": {"node-1": {"name": "es-1"}}}},
    ])

    client = ElasticClient("http://localhost:9200", "key")
    nodes = client.list_nodes()

    assert len(nodes) == 1
    assert nodes[0]["node_id"] == "node-1"


def test_client_max_retries_exceeded(requests_mock):
    requests_mock.get("http://localhost:9200/_nodes", status_code=503)

    client = ElasticClient("http://localhost:9200", "key")
    with pytest.raises(requests.RequestException):
        client._request("GET", "/_nodes")


def test_client_request_exception(requests_mock):
    requests_mock.get("http://localhost:9200/_nodes", exc=requests.ConnectionError("Failed to connect"))

    client = ElasticClient("http://localhost:9200", "key")
    with pytest.raises(requests.RequestException):
        client._request("GET", "/_nodes")


def test_client_list_indices_invalid_format(requests_mock):
    requests_mock.get("http://localhost:9200/_cat/indices?format=json", json={"error": "bad request"})

    client = ElasticClient("http://localhost:9200", "key")
    indices = client.list_indices()

    assert indices == []


def test_client_list_transforms_error(requests_mock):
    requests_mock.get("http://localhost:9200/_transform", status_code=500)

    client = ElasticClient("http://localhost:9200", "key")
    transforms = client.list_transforms()

    assert transforms == []


def test_client_list_nodes_invalid_format(requests_mock):
    # Tests non-dict response payloads
    requests_mock.get("http://localhost:9200/_nodes", json=["invalid_format"])

    client = ElasticClient("http://localhost:9200", "key")
    nodes = client.list_nodes()

    assert nodes == []


def test_client_list_transforms_invalid_format(requests_mock):
    # Tests non-dict response payloads for transforms
    requests_mock.get("http://localhost:9200/_transform", json=["invalid_format"])

    client = ElasticClient("http://localhost:9200", "key")
    transforms = client.list_transforms()

    assert transforms == []
