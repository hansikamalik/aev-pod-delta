from unittest.mock import MagicMock, patch

import pytest

from gitlab_connector.auth import GitLabAuthConfig, GitLabAuthenticator
from gitlab_connector.discovery import GitLabDiscovery, GitLabDiscoveryError


def make_discovery(session):
    auth = GitLabAuthenticator(GitLabAuthConfig(token="t", group="acme"), session=MagicMock())
    return GitLabDiscovery(auth, session=session)


def resp(data, next_url=None, status=200, headers=None):
    r = MagicMock(status_code=status, headers=headers or {}, text="err")
    r.json.return_value = data
    r.links = {"next": {"url": next_url}} if next_url else {}
    return r


def by_project(mapping):
    """session.get side_effect keyed on '/projects/<id>/' substrings."""
    def _get(url, **kwargs):
        for key, value in mapping.items():
            if key in url:
                return value
        raise AssertionError(f"unexpected URL {url}")
    return _get


def test_discover_includes_subgroups_and_follows_link_header():
    s = MagicMock()
    s.get.side_effect = [resp([{"id": 1}], next_url="https://gitlab.com/api/v4/next"), resp([{"id": 2}])]
    projects = make_discovery(s).discover()
    assert [p["id"] for p in projects] == [1, 2]
    first = s.get.call_args_list[0]
    assert first.args[0].endswith("/groups/acme/projects")
    assert first.kwargs["params"]["include_subgroups"] == "true"
    assert s.get.call_args_list[1].kwargs["params"] is None


def test_discover_raises_with_status_code():
    s = MagicMock()
    s.get.return_value = resp([], status=500)
    with pytest.raises(GitLabDiscoveryError) as ei:
        make_discovery(s).discover()
    assert ei.value.status_code == 500


def test_retries_on_429_then_succeeds_and_caps_wait():
    s = MagicMock()
    s.get.side_effect = [resp([], status=429, headers={"Retry-After": "9999"}), resp([{"id": 1}])]
    with patch("gitlab_connector.discovery.time.sleep") as sleeper:
        assert len(make_discovery(s).discover()) == 1
    sleeper.assert_called_once_with(60)


def test_plain_403_is_not_retried():
    s = MagicMock()
    s.get.return_value = resp([], status=403)
    with pytest.raises(GitLabDiscoveryError):
        make_discovery(s).discover()
    assert s.get.call_count == 1


def test_ingest_attaches_only_open_vulnerabilities():
    s = MagicMock()
    s.get.side_effect = by_project({
        "/projects/10/": resp([
            {"id": 1, "state": "detected"}, {"id": 2, "state": "confirmed"},
            {"id": 3, "state": "resolved"}, {"id": 4, "state": "dismissed"},
        ]),
        "/projects/11/": resp([]),
    })
    out = make_discovery(s).ingest([{"id": 10}, {"id": 11}])
    assert [v["id"] for v in out[0]["vulnerabilities"]] == [1, 2]
    assert out[1]["vulnerabilities"] == []


def test_ingest_strips_raw_source_code_extract_recursively():
    s = MagicMock()
    s.get.return_value = resp([{
        "id": 1, "state": "detected", "raw_source_code_extract": "AKIA_TOP_SECRET",
        "finding": {"raw_source_code_extract": "AKIA_TOP_SECRET", "name": "x"},
    }])
    out = make_discovery(s).ingest([{"id": 10}])
    assert "AKIA_TOP_SECRET" not in str(out)
    assert out[0]["vulnerabilities"][0]["finding"]["name"] == "x"


def test_ingest_skips_unavailable_projects_with_single_summary_warning():
    s = MagicMock()
    s.get.side_effect = by_project({
        "/projects/10/": resp([{"id": 1, "state": "detected"}]),
        "/projects/11/": resp([], status=403),
        "/projects/12/": resp([], status=404),
    })
    d = make_discovery(s)
    out = d.ingest([{"id": 10}, {"id": 11}, {"id": 12}])
    assert len(out) == 3 and len(out[0]["vulnerabilities"]) == 1
    assert len(d.warnings) == 1 and "2 of 3" in d.warnings[0] and "403, 404" in d.warnings[0]


def test_ingest_fatal_on_server_error():
    s = MagicMock()
    s.get.return_value = resp([], status=500)
    with pytest.raises(GitLabDiscoveryError):
        make_discovery(s).ingest([{"id": 10}])


def test_ingest_resets_warnings_each_run():
    s = MagicMock()
    s.get.return_value = resp([], status=403)
    d = make_discovery(s)
    d.ingest([{"id": 10}])
    d.ingest([{"id": 10}])
    assert len(d.warnings) == 1
