from unittest.mock import MagicMock, patch

import pytest

from sentinelone_connector.auth import SentinelOneAuthConfig, SentinelOneAuthenticator
from sentinelone_connector.discovery import SentinelOneDiscovery, SentinelOneDiscoveryError


def make_discovery(session):
    auth = SentinelOneAuthenticator(
        SentinelOneAuthConfig(base_url="https://acme.sentinelone.net", api_token="t"),
        session=MagicMock(),
    )
    return SentinelOneDiscovery(auth, session=session)


def page(data, next_cursor=None, status=200, headers=None):
    resp = MagicMock(status_code=status, headers=headers or {}, text="err")
    resp.json.return_value = {"data": data, "pagination": {"nextCursor": next_cursor}}
    return resp


def test_discover_follows_cursor_pagination():
    session = MagicMock()
    session.get.side_effect = [page([{"id": "1"}], "c2"), page([{"id": "2"}], None)]
    agents = make_discovery(session).discover()
    assert [a["id"] for a in agents] == ["1", "2"]
    assert session.get.call_args_list[1].kwargs["params"]["cursor"] == "c2"


def test_discover_raises_on_error():
    session = MagicMock()
    session.get.return_value = page([], status=500)
    with pytest.raises(SentinelOneDiscoveryError):
        make_discovery(session).discover()


def test_retries_on_429_then_succeeds():
    session = MagicMock()
    session.get.side_effect = [page([], status=429, headers={"Retry-After": "0"}), page([{"id": "1"}])]
    with patch("sentinelone_connector.discovery.time.sleep") as sleeper:
        agents = make_discovery(session).discover()
    assert len(agents) == 1
    sleeper.assert_called_once_with(0)


def test_ingest_attaches_threats_to_agents():
    session = MagicMock()
    session.get.return_value = page(
        [{"id": "t1", "agentRealtimeInfo": {"agentId": "a1"}}]
    )
    out = make_discovery(session).ingest([{"id": "a1"}, {"id": "a2"}])
    assert len(out[0]["threats"]) == 1
    assert out[1]["threats"] == []


def test_ingest_keeps_orphaned_threats():
    session = MagicMock()
    session.get.return_value = page([{"id": "t9", "agentRealtimeInfo": {"agentId": "gone"}}])
    out = make_discovery(session).ingest([{"id": "a1"}])
    assert out[-1]["_orphaned_threats"] is True
    assert out[-1]["threats"][0]["id"] == "t9"
