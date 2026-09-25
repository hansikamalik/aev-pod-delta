from unittest.mock import MagicMock

from sentinel_connector.auth import SentinelAuthConfig, SentinelAuthenticator
from sentinel_connector.discovery import SentinelDiscovery


def make_authenticator():
    config = SentinelAuthConfig(
        tenant_id="t1",
        client_id="c1",
        client_secret="s1",
        subscription_id="sub1",
        resource_group="rg1",
        workspace_name="ws1",
    )
    authenticator = MagicMock(spec=SentinelAuthenticator)
    authenticator.config = config
    authenticator.auth_headers.return_value = {"Authorization": "Bearer tok"}
    return authenticator


def test_discover_single_page():
    session = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"value": [{"name": "incident-1"}, {"name": "incident-2"}]}
    session.get.return_value = resp

    discovery = SentinelDiscovery(make_authenticator(), session=session)
    incidents = discovery.discover()

    assert len(incidents) == 2
    assert incidents[0]["name"] == "incident-1"


def test_discover_paginates_with_nextlink():
    session = MagicMock()
    page1 = MagicMock(status_code=200)
    page1.json.return_value = {
        "value": [{"name": "incident-1"}],
        "nextLink": "https://management.azure.com/next?page=2",
    }
    page2 = MagicMock(status_code=200)
    page2.json.return_value = {"value": [{"name": "incident-2"}]}
    session.get.side_effect = [page1, page2]

    discovery = SentinelDiscovery(make_authenticator(), session=session)
    incidents = discovery.discover()

    assert len(incidents) == 2
    assert session.get.call_count == 2


def test_ingest_enriches_with_entities():
    session = MagicMock()
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"entities": [{"kind": "host", "name": "e1"}]}
    session.post.return_value = resp

    discovery = SentinelDiscovery(make_authenticator(), session=session)
    incidents = [{"name": "incident-1"}]
    enriched = discovery.ingest(incidents)

    assert enriched[0]["entities"][0]["kind"] == "host"


def test_ingest_handles_entity_fetch_failure_gracefully():
    session = MagicMock()
    resp = MagicMock(status_code=500, text="server error")
    session.post.return_value = resp

    discovery = SentinelDiscovery(make_authenticator(), session=session)
    incidents = [{"name": "incident-1"}]
    enriched = discovery.ingest(incidents)

    assert enriched[0]["entities"] == []
