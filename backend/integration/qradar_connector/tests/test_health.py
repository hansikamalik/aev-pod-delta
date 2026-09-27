from unittest.mock import patch
from qradar_connector.connector import QRadarConnector

def test_check_health_success():
    config = {"host": "qradar.local"}
    creds = {"sec_token": "valid_token"}
    connector = QRadarConnector(config, creds)

    with patch.object(connector.client, "ping", return_value=True):
        assert connector.check_health() is True

def test_check_health_failure():
    config = {"host": "qradar.local"}
    creds = {"sec_token": "invalid_token"}
    connector = QRadarConnector(config, creds)

    with patch.object(connector.client, "ping", return_value=False):
        assert connector.check_health() is False
