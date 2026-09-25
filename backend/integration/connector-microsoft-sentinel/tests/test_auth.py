import time
from unittest.mock import MagicMock

import pytest

from sentinel_connector.auth import (
    SentinelAuthConfig,
    SentinelAuthenticator,
    SentinelAuthError,
)


def make_config():
    return SentinelAuthConfig(
        tenant_id="tenant-123",
        client_id="client-abc",
        client_secret="secret-xyz",
        subscription_id="sub-1",
        resource_group="rg-1",
        workspace_name="ws-1",
    )


def make_session(status_code=200, json_body=None):
    session = MagicMock()
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body or {"access_token": "tok-1", "expires_in": 3600}
    resp.text = "error body"
    session.post.return_value = resp
    return session


def test_get_token_success():
    session = make_session()
    authenticator = SentinelAuthenticator(make_config(), session=session)
    token = authenticator.get_token()
    assert token == "tok-1"
    session.post.assert_called_once()


def test_get_token_caches_until_near_expiry():
    session = make_session(json_body={"access_token": "tok-1", "expires_in": 3600})
    authenticator = SentinelAuthenticator(make_config(), session=session)
    authenticator.get_token()
    authenticator.get_token()
    assert session.post.call_count == 1


def test_get_token_refreshes_when_expired():
    session = make_session(json_body={"access_token": "tok-1", "expires_in": 3600})
    authenticator = SentinelAuthenticator(make_config(), session=session)
    authenticator.get_token()
    authenticator._expires_at = time.time() - 1  # force expiry
    authenticator.get_token()
    assert session.post.call_count == 2


def test_get_token_raises_on_failure():
    session = make_session(status_code=401)
    authenticator = SentinelAuthenticator(make_config(), session=session)
    with pytest.raises(SentinelAuthError):
        authenticator.get_token()


def test_validate_returns_false_on_auth_error():
    session = make_session(status_code=403)
    authenticator = SentinelAuthenticator(make_config(), session=session)
    assert authenticator.validate() is False


def test_validate_returns_true_on_success():
    session = make_session()
    authenticator = SentinelAuthenticator(make_config(), session=session)
    assert authenticator.validate() is True


def test_auth_headers_include_bearer_token():
    session = make_session()
    authenticator = SentinelAuthenticator(make_config(), session=session)
    headers = authenticator.auth_headers()
    assert headers["Authorization"] == "Bearer tok-1"
