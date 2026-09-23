"""
Integration test exercising the full auth -> discover -> ingest ->
normalize -> push pipeline against a sandboxed/mocked Sentinel API
and mocked Vault + Beta platform.

Mirrors the "sandbox test" step in the plan's per-connector pattern.
"""

from unittest.mock import MagicMock, patch

from sentinel_connector.connector import SentinelConnector
from sentinel_connector.credentials import MockVaultClient


def make_vault():
    return MockVaultClient(
        {
            "secret/connectors/microsoft-sentinel/org-1": {
                "tenant_id": "t1",
                "client_id": "c1",
                "client_secret": "s1",
                "subscription_id": "sub1",
                "resource_group": "rg1",
                "workspace_name": "ws1",
            }
        }
    )


def make_incident_response():
    resp = MagicMock(status_code=200)
    resp.json.return_value = {
        "value": [
            {
                "name": "incident-1",
                "properties": {
                    "severity": "High",
                    "title": "Suspicious sign-in",
                    "description": "desc",
                    "createdTimeUtc": "2026-09-05T10:00:00Z",
                },
            }
        ]
    }
    return resp


def test_full_sync_pipeline():
    # IMPORTANT: auth.py, discovery.py, and push.py each do `import requests`,
    # so they all share the *same* `requests` module object. Patching
    # `requests.Session` from three different module paths patches the
    # same underlying attribute three times — the last patch silently wins
    # for all three call sites. Patch it once, globally, and hand out a
    # different mock session per instantiation via side_effect instead
    # (SentinelConnector.__init__ builds them in this order: auth, discovery,
    # push — see connector.py).
    auth_session = MagicMock()
    auth_session.post.return_value = MagicMock(
        status_code=200, json=lambda: {"access_token": "tok", "expires_in": 3600}
    )

    discovery_session = MagicMock()
    discovery_session.get.return_value = make_incident_response()
    entities_resp = MagicMock(status_code=200)
    entities_resp.json.return_value = {
        "entities": [{"kind": "host", "name": "e1", "properties": {"hostName": "web-01"}}]
    }
    discovery_session.post.return_value = entities_resp

    push_session = MagicMock()
    push_session.post.return_value = MagicMock(status_code=200)

    with patch("requests.Session", side_effect=[auth_session, discovery_session, push_session]):
        connector = SentinelConnector(vault=make_vault(), org_id="org-1", beta_api_token="beta-tok")
        result = connector.run_full_sync()

    assert result.success is True
    assert result.assets_count == 1


def test_health_check_reflects_auth_state():
    auth_session = MagicMock()
    auth_session.post.return_value = MagicMock(status_code=401, text="unauthorized")

    with patch("requests.Session", return_value=auth_session):
        connector = SentinelConnector(vault=make_vault(), org_id="org-1", beta_api_token="beta-tok")
        assert connector.health_check() is False
