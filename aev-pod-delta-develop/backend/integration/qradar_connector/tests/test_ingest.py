from unittest.mock import MagicMock
from qradar_connector.connector import QRadarConnector
from qradar_connector.models import Asset

def test_ingest_pushes_assets():
    connector = QRadarConnector({"host": "qradar.local"}, {"sec_token": "token"})
    connector.platform_client = MagicMock()
    connector.platform_client.bulk_upsert.return_value = 2

    assets = [
        Asset(id="1", source="qradar", type="compute", name="a1", raw={}),
        Asset(id="2", source="qradar", type="compute", name="a2", raw={})
    ]

    pushed_count = connector.ingest(assets)
    assert pushed_count == 2
    connector.platform_client.bulk_upsert.assert_called_once_with(assets)
