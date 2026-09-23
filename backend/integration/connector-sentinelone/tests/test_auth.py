from unittest.mock import MagicMock

import requests

from sentinelone_connector.auth import SentinelOneAuthConfig, SentinelOneAuthenticator


def make_config():
    return SentinelOneAuthConfig(base_url="https://acme.sentinelone.net/", api_token="tok-1")


def test_api_base_normalises_trailing_slash():
    assert make_config().api_base == "https://acme.sentinelone.net/web/api/v2.1"


def test_auth_headers_use_apitoken_scheme():
    headers = SentinelOneAuthenticator(make_config(), session=MagicMock()).auth_headers()
    assert headers["Authorization"] == "ApiToken tok-1"


def test_validate_true_on_200():
    session = MagicMock()
    session.get.return_value = MagicMock(status_code=200)
    assert SentinelOneAuthenticator(make_config(), session=session).validate() is True
    assert session.get.call_args.kwargs["params"] == {"limit": 1}


def test_validate_false_on_401():
    session = MagicMock()
    session.get.return_value = MagicMock(status_code=401)
    assert SentinelOneAuthenticator(make_config(), session=session).validate() is False


def test_validate_false_on_network_error():
    session = MagicMock()
    session.get.side_effect = requests.ConnectionError("boom")
    assert SentinelOneAuthenticator(make_config(), session=session).validate() is False
