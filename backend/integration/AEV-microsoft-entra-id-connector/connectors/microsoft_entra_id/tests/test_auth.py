import time
import pytest
from unittest.mock import MagicMock

from connectors.microsoft_entra_id.auth import EntraIDAuth, EntraIDAuthError


def _resp(json_body=None, status=200, text=""):
    r = MagicMock()
    r.status_code = status
    r.text = text
    r.json.return_value = json_body or {}
    return r


def make_auth(session=None):
    return EntraIDAuth(tenant_id="t", client_id="c", client_secret="s", session=session)


def test_token_acquired_and_cached():
    session = MagicMock()
    session.post.return_value = _resp({"access_token": "tok", "expires_in": 3600})
    auth = make_auth(session)
    assert auth.token() == "tok"
    assert auth.token() == "tok"
    assert session.post.call_count == 1


def test_refresh_before_expiry():
    session = MagicMock()
    session.post.return_value = _resp({"access_token": "tok", "expires_in": 60})
    auth = make_auth(session)
    auth.token()
    auth._expires_at = time.time() + 30  # within the 120s margin
    auth.token()
    assert session.post.call_count == 2


def test_token_failure_raises():
    session = MagicMock()
    session.post.return_value = _resp(status=400, text="invalid_client")
    with pytest.raises(EntraIDAuthError):
        make_auth(session).token()


def test_introspect_hits_graph():
    session = MagicMock()
    session.post.return_value = _resp({"access_token": "tok", "expires_in": 3600})
    session.get.return_value = _resp({"value": [{"displayName": "Contoso"}]})
    auth = make_auth(session)
    body = auth.introspect()
    assert body["value"][0]["displayName"] == "Contoso"
    assert session.get.call_args.args[0].startswith("https://graph.microsoft.com")


def test_introspect_failure_raises():
    session = MagicMock()
    session.post.return_value = _resp({"access_token": "tok", "expires_in": 3600})
    session.get.return_value = _resp(status=401, text="unauthorized")
    with pytest.raises(EntraIDAuthError):
        make_auth(session).introspect()
