from unittest.mock import MagicMock

import requests

from gitlab_connector.auth import GitLabAuthConfig, GitLabAuthenticator


def cfg(**kw):
    return GitLabAuthConfig(token="tok", group=kw.pop("group", "acme"), **kw)


def test_default_api_base():
    assert cfg().api_base == "https://gitlab.com/api/v4"


def test_self_managed_url_gets_api_suffix_appended():
    assert cfg(api_url="https://gitlab.acme.com/").api_base == "https://gitlab.acme.com/api/v4"


def test_api_suffix_not_duplicated():
    assert cfg(api_url="https://gitlab.acme.com/api/v4/").api_base == "https://gitlab.acme.com/api/v4"


def test_group_path_is_url_encoded():
    assert cfg(group="acme/platform").group_ref == "acme%2Fplatform"


def test_headers_use_private_token():
    assert GitLabAuthenticator(cfg(), session=MagicMock()).auth_headers()["PRIVATE-TOKEN"] == "tok"


def test_validate_true_on_200_and_hits_group_endpoint():
    s = MagicMock()
    s.get.return_value = MagicMock(status_code=200)
    assert GitLabAuthenticator(cfg(group="acme/platform"), session=s).validate() is True
    assert s.get.call_args.args[0] == "https://gitlab.com/api/v4/groups/acme%2Fplatform"


def test_validate_false_on_401():
    s = MagicMock()
    s.get.return_value = MagicMock(status_code=401)
    assert GitLabAuthenticator(cfg(), session=s).validate() is False


def test_validate_false_on_network_error():
    s = MagicMock()
    s.get.side_effect = requests.ConnectionError("boom")
    assert GitLabAuthenticator(cfg(), session=s).validate() is False
