from unittest.mock import MagicMock, patch

import pytest

from github_connector.auth import GitHubAuthConfig, GitHubAuthenticator
from github_connector.discovery import GitHubDiscovery, GitHubDiscoveryError


def make_discovery(session):
    auth = GitHubAuthenticator(GitHubAuthConfig(token="t", org="acme"), session=MagicMock())
    return GitHubDiscovery(auth, session=session)


def resp(data, next_url=None, status=200, headers=None):
    r = MagicMock(status_code=status, headers=headers or {}, text="err")
    r.json.return_value = data
    r.links = {"next": {"url": next_url}} if next_url else {}
    return r


def route(mapping):
    """Return a session.get side_effect that answers by URL substring."""
    def _get(url, **kwargs):
        for key, value in mapping.items():
            if key in url:
                return value
        raise AssertionError(f"unexpected URL {url}")
    return _get


def test_discover_follows_link_header_pagination():
    s = MagicMock()
    s.get.side_effect = [resp([{"id": 1}], next_url="https://api.github.com/next"), resp([{"id": 2}])]
    repos = make_discovery(s).discover()
    assert [r["id"] for r in repos] == [1, 2]
    assert s.get.call_args_list[1].args[0] == "https://api.github.com/next"
    assert s.get.call_args_list[1].kwargs["params"] is None


def test_discover_raises_with_status_code():
    s = MagicMock()
    s.get.return_value = resp([], status=500)
    with pytest.raises(GitHubDiscoveryError) as ei:
        make_discovery(s).discover()
    assert ei.value.status_code == 500


def test_retries_on_429_then_succeeds():
    s = MagicMock()
    s.get.side_effect = [resp([], status=429, headers={"Retry-After": "0"}), resp([{"id": 1}])]
    with patch("github_connector.discovery.time.sleep") as sleeper:
        repos = make_discovery(s).discover()
    assert len(repos) == 1
    sleeper.assert_called_once_with(0)


def test_retries_on_403_rate_limit_and_caps_wait():
    s = MagicMock()
    limited = resp([], status=403, headers={"X-RateLimit-Remaining": "0", "Retry-After": "9999"})
    s.get.side_effect = [limited, resp([{"id": 1}])]
    with patch("github_connector.discovery.time.sleep") as sleeper:
        make_discovery(s).discover()
    sleeper.assert_called_once_with(60)


def test_plain_403_is_not_retried():
    s = MagicMock()
    s.get.return_value = resp([], status=403)
    with pytest.raises(GitHubDiscoveryError):
        make_discovery(s).discover()
    assert s.get.call_count == 1


def test_ingest_attaches_alerts_and_tags_type():
    s = MagicMock()
    s.get.side_effect = route({
        "dependabot": resp([{"number": 1, "repository": {"id": 10}}]),
        "code-scanning": resp([{"number": 2, "repository": {"id": 10}}]),
        "secret-scanning": resp([]),
    })
    out = make_discovery(s).ingest([{"id": 10}, {"id": 11}])
    assert {a["_alert_type"] for a in out[0]["alerts"]} == {"dependabot", "code_scanning"}
    assert out[1]["alerts"] == []


def test_ingest_requests_open_alerts_only():
    s = MagicMock()
    s.get.return_value = resp([])
    make_discovery(s).ingest([])
    assert all(c.kwargs["params"]["state"] == "open" for c in s.get.call_args_list)


def test_ingest_strips_leaked_secret_value():
    s = MagicMock()
    s.get.side_effect = route({
        "dependabot": resp([]),
        "code-scanning": resp([]),
        "secret-scanning": resp([{"number": 3, "secret": "ghp_SUPERSECRET", "repository": {"id": 10}}]),
    })
    out = make_discovery(s).ingest([{"id": 10}])
    assert "secret" not in out[0]["alerts"][0]
    assert "ghp_SUPERSECRET" not in str(out)


def test_ingest_skips_disabled_alert_type_with_warning():
    s = MagicMock()
    s.get.side_effect = route({
        "dependabot": resp([{"number": 1, "repository": {"id": 10}}]),
        "code-scanning": resp([], status=404),
        "secret-scanning": resp([], status=403),
    })
    d = make_discovery(s)
    out = d.ingest([{"id": 10}])
    assert len(out[0]["alerts"]) == 1
    assert len(d.warnings) == 2


def test_ingest_fatal_on_server_error():
    s = MagicMock()
    s.get.return_value = resp([], status=500)
    with pytest.raises(GitHubDiscoveryError):
        make_discovery(s).ingest([{"id": 10}])


def test_ingest_keeps_orphaned_alerts():
    s = MagicMock()
    s.get.side_effect = route({
        "dependabot": resp([{"number": 9, "repository": {"id": 999}}]),
        "code-scanning": resp([]),
        "secret-scanning": resp([]),
    })
    out = make_discovery(s).ingest([{"id": 10}])
    assert out[-1]["_orphaned_alerts"] is True
