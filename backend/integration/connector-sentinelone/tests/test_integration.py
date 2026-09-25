"""
Full auth -> discover -> ingest -> normalize -> push pipeline against a
mocked SentinelOne API, Vault and Beta platform.

Sessions are handed out via side_effect in the order SentinelOneConnector
builds them: auth, discovery, push (see connector.py).
"""

from unittest.mock import MagicMock, patch

from sentinelone_connector.connector import SentinelOneConnector
from sentinelone_connector.credentials import MockVaultClient


def make_vault():
    return MockVaultClient(
        {"secret/connectors/sentinelone/org-1": {"base_url": "https://acme.sentinelone.net", "api_token": "t"}}
    )


def resp(data):
    r = MagicMock(status_code=200, headers={})
    r.json.return_value = {"data": data, "pagination": {"nextCursor": None}}
    return r


def test_full_sync_pipeline():
    auth_session = MagicMock()
    auth_session.get.return_value = MagicMock(status_code=200)

    discovery_session = MagicMock()
    discovery_session.get.side_effect = [
        resp([{"id": "a1", "computerName": "web-01", "machineType": "server"}]),
        resp([{
            "id": "t1",
            "threatInfo": {"threatName": "evil", "confidenceLevel": "malicious"},
            "agentRealtimeInfo": {"agentId": "a1"},
        }]),
    ]

    push_session = MagicMock()
    push_session.post.return_value = MagicMock(status_code=200)

    with patch("requests.Session", side_effect=[auth_session, discovery_session, push_session]):
        connector = SentinelOneConnector(vault=make_vault(), org_id="org-1", beta_api_token="beta")
        result = connector.run_full_sync()

    assert result.success is True
    assert result.assets_count == 1
    assert result.findings_count == 1
    assert connector.findings[0].severity == "high"


def test_health_check_reflects_auth_state():
    auth_session = MagicMock()
    auth_session.get.return_value = MagicMock(status_code=401)
    with patch("requests.Session", return_value=auth_session):
        connector = SentinelOneConnector(vault=make_vault(), org_id="org-1", beta_api_token="beta")
        assert connector.health_check() is False
        assert connector.run_full_sync().errors == ["Authentication failed"]
