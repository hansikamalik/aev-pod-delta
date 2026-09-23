import requests
import requests_mock
from elastic_connector.connector import ElasticConnector


def test_check_health_success(requests_mock):
    requests_mock.get("http://localhost:9200/", json={"tagline": "You Know, for Search"})

    connector = ElasticConnector(
        config={"endpoint": "http://localhost:9200"},
        credentials={"api_key": "valid_key"}
    )
    assert connector.check_health() is True


def test_check_health_failure(requests_mock):
    requests_mock.get("http://localhost:9200/", status_code=401)

    connector = ElasticConnector(
        config={"endpoint": "http://localhost:9200"},
        credentials={"api_key": "invalid_key"}
    )
    assert connector.check_health() is False


def test_check_health_exception(requests_mock):
    requests_mock.get("http://localhost:9200/", exc=requests.RequestException("Network Error"))

    connector = ElasticConnector(
        config={"endpoint": "http://localhost:9200"},
        credentials={"api_key": "invalid_key"}
    )
    assert connector.check_health() is False
