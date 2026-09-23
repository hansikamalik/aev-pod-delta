"""
Full auth -> discover -> ingest -> normalize -> push pipeline against a mocked
GitHub API, Vault and Beta platform. Sessions are handed out in the order
GitHubConnector builds them: auth, discovery, push (see connector.py).
"""

from unittest.mock import MagicMock, patch

from github_connector.connector import GitHubConnector
from github_connector.credentials import MockVaultClient


def make_vault():
    return MockVaultClient({"secret/connectors/github/org-1": {"token": "t", "org": "acme"}})


def resp(data, status=200):
    r = MagicMock(status_code=status, headers={}, text="")
    r.json.return_value = data
    r.links = {}
    return r


def discovery_get(url, **kwargs):
    if url.endswith("/repos"):
        return resp([{"id": 10, "full_name": "acme/api", "visibility": "private"}])
    if "dependabot" in url:
        return resp([{"number": 1, "repository": {"id": 10, "full_name": "acme/api"},
                      "security_advisory": {"severity": "high", "summary": "bad dep"},
                      "created_at": "2026-09-05T00:00:00Z"}])
    if "code-scanning" in url:
        return resp([], status=404)  # feature not enabled -> warning, not failure
    return resp([{"number": 2, "secret": "ghp_LEAK", "repository": {"id": 10, "full_name": "acme/api"}}])


def test_full_sync_pipeline():
    auth_session = MagicMock()
    auth_session.get.return_value = MagicMock(status_code=200)
    discovery_session = MagicMock()
    discovery_session.get.side_effect = discovery_get
    push_session = MagicMock()
    push_session.post.return_value = MagicMock(status_code=200)

    with patch("requests.Session", side_effect=[auth_session, discovery_session, push_session]):
        c = GitHubConnector(vault=make_vault(), org_id="org-1", beta_api_token="beta")
        result = c.run_full_sync()

    assert result.success is True
    assert result.assets_count == 1 and result.findings_count == 2
    assert {f.severity for f in c.findings} == {"high"}
    assert c.warnings == ["code_scanning alerts skipped (HTTP 404)"]
    assert "ghp_LEAK" not in str(c.findings) and "ghp_LEAK" not in str(push_session.post.call_args)


def test_health_check_reflects_auth_state():
    auth_session = MagicMock()
    auth_session.get.return_value = MagicMock(status_code=401)
    with patch("requests.Session", return_value=auth_session):
        c = GitHubConnector(vault=make_vault(), org_id="org-1", beta_api_token="beta")
        assert c.health_check() is False
        assert c.run_full_sync().errors == ["Authentication failed"]
