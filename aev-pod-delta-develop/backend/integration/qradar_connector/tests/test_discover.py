from unittest.mock import patch
from qradar_connector.connector import QRadarConnector
from qradar_connector.models import Asset

MOCK_QRADAR_RESPONSE = [
    {
        "id": 1001,
        "host_names": [{"name": "qradar-console.internal"}],
        "interfaces": [{"ip_addresses": [{"ip_address": "192.168.1.50"}]}],
        "offense_count": 0,
        "domain_id": 1
    }
]

def test_discover_returns_valid_assets():
    connector = QRadarConnector({"host": "qradar.local"}, {"sec_token": "token"})

    with patch.object(connector.client, "list_assets", return_value=MOCK_QRADAR_RESPONSE):
        assets = list(connector.discover())

        assert len(assets) == 1
        asset = assets[0]
        
        assert isinstance(asset, Asset)
        assert asset.id == "1001"
        assert asset.source == connector.name
        assert asset.name == "qradar-console.internal"
        assert asset.type == "network"
        assert asset.raw == MOCK_QRADAR_RESPONSE[0]
