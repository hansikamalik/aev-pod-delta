from unittest.mock import MagicMock

import requests

from github_connector.auth import GitHubAuthConfig, GitHubAuthenticator


def cfg(**kw):
    return GitHubAuthConfig(token="tok", org="acme", **kw)


def test_api_base_strips_trailing_slash():
    assert cfg(api_url="https://ghe.acme.com/api/v3/").api_base == "https://ghe.acme.com/api/v3"


def test_default_api_url():
    assert cfg().api_base == "https://api.github.com"


def test_headers():
    h = GitHubAuthenticator(cfg(), session=MagicMock()).auth_headers()
    assert h["Authorization"] == "Bearer tok"
    assert h["Accept"] == "application/vnd.github+json"
    assert "X-GitHub-Api-Version" in h


def test_validate_true_on_200_and_calls_org_endpoint():
    s = MagicMock()
    s.get.return_value = MagicMock(status_code=200)
    assert GitHubAuthenticator(cfg(), session=s).validate() is True
    assert s.get.call_args.args[0] == "https://api.github.com/orgs/acme"


def test_validate_false_on_401():
    s = MagicMock()
    s.get.return_value = MagicMock(status_code=401)
    assert GitHubAuthenticator(cfg(), session=s).validate() is False


def test_validate_false_on_network_error():
    s = MagicMock()
    s.get.side_effect = requests.ConnectionError("boom")
    assert GitHubAuthenticator(cfg(), session=s).validate() is False
