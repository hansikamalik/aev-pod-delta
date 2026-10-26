import time
from unittest.mock import Mock

import pytest
import requests

from google_workspace_auth import (
    AuthenticationError,
    ConfigurationError,
    GoogleWorkspaceAuthenticator,
)

PRIVATE_KEY = "TEST-ONLY-PRIVATE-KEY"


def make_auth(http_post):
    auth = GoogleWorkspaceAuthenticator(
        client_email="svc@example.iam.gserviceaccount.com",
        private_key=PRIVATE_KEY,
        delegated_subject="admin@example.com",
        scopes=["https://www.googleapis.com/auth/admin.directory.user.readonly"],
        http_post=http_post,
    )
    auth._build_assertion = Mock(return_value="fake-jwt")
    return auth


def response(payload):
    r = Mock()
    r.raise_for_status.return_value = None
    r.json.return_value = payload
    return r


def test_successful_token_exchange():
    post = Mock(return_value=response({"access_token": "token-1", "expires_in": 3600}))
    auth = make_auth(post)
    token = auth.get_token()
    assert token.access_token == "token-1"
    assert token.is_valid()
    post.assert_called_once()


def test_token_is_cached():
    post = Mock(return_value=response({"access_token": "token-1", "expires_in": 3600}))
    auth = make_auth(post)
    first = auth.get_token()
    second = auth.get_token()
    assert first == second
    post.assert_called_once()


def test_expired_token_is_refreshed():
    post = Mock(side_effect=[
        response({"access_token": "token-1", "expires_in": 3600}),
        response({"access_token": "token-2", "expires_in": 3600}),
    ])
    auth = make_auth(post)
    auth.get_token()
    auth._token = auth._token.__class__(access_token="expired", expires_at=time.time() - 1)
    assert auth.get_token().access_token == "token-2"
    assert post.call_count == 2


def test_invalidate_forces_refresh():
    post = Mock(side_effect=[
        response({"access_token": "token-1", "expires_in": 3600}),
        response({"access_token": "token-2", "expires_in": 3600}),
    ])
    auth = make_auth(post)
    assert auth.get_token().access_token == "token-1"
    auth.invalidate()
    assert auth.get_token().access_token == "token-2"


def test_network_failure():
    post = Mock(side_effect=requests.RequestException("network down"))
    auth = make_auth(post)
    with pytest.raises(AuthenticationError):
        auth.get_token()


def test_invalid_json():
    r = Mock()
    r.raise_for_status.return_value = None
    r.json.side_effect = ValueError("bad json")
    auth = make_auth(Mock(return_value=r))
    with pytest.raises(AuthenticationError):
        auth.get_token()


def test_missing_access_token():
    auth = make_auth(Mock(return_value=response({"expires_in": 3600})))
    with pytest.raises(AuthenticationError):
        auth.get_token()


def test_invalid_expiry():
    auth = make_auth(Mock(return_value=response({"access_token": "token", "expires_in": 0})))
    with pytest.raises(AuthenticationError):
        auth.get_token()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"client_email": "", "private_key": PRIVATE_KEY, "delegated_subject": "admin@example.com"},
        {"client_email": "svc@example.com", "private_key": "", "delegated_subject": "admin@example.com"},
        {"client_email": "svc@example.com", "private_key": PRIVATE_KEY, "delegated_subject": ""},
    ],
)
def test_required_configuration(kwargs):
    with pytest.raises(ConfigurationError):
        GoogleWorkspaceAuthenticator(**kwargs)


def test_authorization_header():
    post = Mock(return_value=response({"access_token": "token-1", "expires_in": 3600}))
    auth = make_auth(post)
    assert auth.authorization_header() == {"Authorization": "Bearer token-1"}
