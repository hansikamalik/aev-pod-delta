import base64
import json
import time

import pytest
import requests

from connectors.servicenow.auth import ServiceNowAuth, ServiceNowAuthError


class _Resp:
    def __init__(self, status=200, payload=None, text=""):
        self.status_code = status
        self._payload = payload or {}
        self.text = text or json.dumps(self._payload)
        self.content = b"{}"

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.posts = []
        self.gets = []

    def post(self, url, data=None, timeout=None):
        self.posts.append((url, data))
        return _Resp(200, {"access_token": "tok-123", "expires_in": 1800})

    def get(self, url, headers=None, params=None, timeout=None):
        self.gets.append((url, headers, params))
        return _Resp(200, {"result": []})


def test_basic_auth_header():
    auth = ServiceNowAuth("https://x.service-now.com", method="basic",
                          username="u", password="p", session=FakeSession())
    hdr = auth.auth_headers()["Authorization"]
    expected = "Basic " + base64.b64encode(b"u:p").decode()
    assert hdr == expected


def test_oauth_fetches_and_caches_token():
    sess = FakeSession()
    auth = ServiceNowAuth("https://x.service-now.com", method="oauth",
                          username="u", password="p",
                          oauth_client_id="cid", oauth_client_secret="cs", session=sess)
    assert auth.auth_headers()["Authorization"] == "Bearer tok-123"
    assert auth.auth_headers()["Authorization"] == "Bearer tok-123"
    assert len(sess.posts) == 1  # cached, not re-fetched


def test_oauth_refreshes_expired_token():
    sess = FakeSession()
    auth = ServiceNowAuth("https://x.service-now.com", method="oauth",
                          username="u", password="p",
                          oauth_client_id="cid", oauth_client_secret="cs", session=sess)
    auth.auth_headers()
    auth._token.expires_at = time.time() - 1  # force expiry
    auth.auth_headers()
    assert len(sess.posts) == 2


def test_basic_requires_credentials():
    with pytest.raises(ServiceNowAuthError):
        ServiceNowAuth("https://x.service-now.com", method="basic", session=FakeSession())


def test_token_failure_raises():
    class BadSession(FakeSession):
        def post(self, url, data=None, timeout=None):
            return _Resp(401, text="unauthorized")

    auth = ServiceNowAuth("https://x.service-now.com", method="oauth",
                          username="u", password="p",
                          oauth_client_id="c", oauth_client_secret="s", session=BadSession())
    with pytest.raises(ServiceNowAuthError):
        auth.auth_headers()
