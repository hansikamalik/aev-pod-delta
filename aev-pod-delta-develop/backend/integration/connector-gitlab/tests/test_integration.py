"""
Full auth -> discover -> ingest -> normalize -> push pipeline against a mocked
GitLab API, Vault and Beta platform. Sessions are handed out in the order
GitLabConnector builds them: auth, discovery, push (see connector.py).
"""

from unittest.mock import MagicMock, patch

from gitlab_connector.connector import GitLabConnector
from gitlab_connector.credentials import MockVaultClient


def make_vault():
    return MockVaultClient({"secret/connectors/gitlab/org-1": {"token": "t", "group": "acme"}})


def resp(data, status=200):
    r = MagicMock(status_code=status, headers={}, text="")
    r.json.return_value = data
    r.links = {}
    return r


def discovery_get(url, **kwargs):
    if url.endswith("/projects"):
        return resp([
            {"id": 10, "path_with_namespace": "acme/api", "visibility": "private"},
            {"id": 11, "path_with_namespace": "acme/web", "visibility": "internal"},
        ])
    if "/projects/10/vulnerabilities" in url:
        return resp([
            {"id": 1, "title": "XSS", "severity": "medium", "state": "detected", "report_type": "sast",
             "raw_source_code_extract": "LEAK"},
            {"id": 2, "title": "old", "severity": "low", "state": "resolved"},
        ])
    return resp([], status=403)  # project 11: no Ultimate -> skipped with warning


def test_full_sync_pipeline():
    auth_session = MagicMock()
    auth_session.get.return_value = MagicMock(status_code=200)
    discovery_session = MagicMock()
    discovery_session.get.side_effect = discovery_get
    push_session = MagicMock()
    push_session.post.return_value = MagicMock(status_code=200)

    with patch("requests.Session", side_effect=[auth_session, discovery_session, push_session]):
        c = GitLabConnector(vault=make_vault(), org_id="org-1", beta_api_token="beta")
        result = c.run_full_sync()

    assert result.success is True
    assert result.assets_count == 2 and result.findings_count == 1
    assert c.findings[0].severity == "medium" and c.findings[0].asset_external_id == "10"
    assert len(c.warnings) == 1 and "1 of 2" in c.warnings[0]
    assert "LEAK" not in str(c.findings)


def test_health_check_reflects_auth_state():
    auth_session = MagicMock()
    auth_session.get.return_value = MagicMock(status_code=401)
    with patch("requests.Session", return_value=auth_session):
        c = GitLabConnector(vault=make_vault(), org_id="org-1", beta_api_token="beta")
        assert c.health_check() is False
        assert c.run_full_sync().errors == ["Authentication failed"]
