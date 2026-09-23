import unittest
from unittest.mock import patch

import requests

from microsoft365_connector.auth import GraphAuthenticator
from microsoft365_connector.exceptions import AuthenticationError


def _fake_post_success(*args, **kwargs):
    class R:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"access_token": "fake-token", "expires_in": 3600}

    return R()


def _fake_post_failure(*args, **kwargs):
    raise requests.RequestException("network down")


class TestGraphAuthenticator(unittest.TestCase):
    def test_get_token_success(self):
        authenticator = GraphAuthenticator("tenant", "client", "secret")
        with patch("microsoft365_connector.auth.requests.post", side_effect=_fake_post_success):
            token = authenticator.get_token()
        self.assertEqual(token.access_token, "fake-token")
        self.assertTrue(token.is_valid())

    def test_get_token_caches_until_expiry(self):
        authenticator = GraphAuthenticator("tenant", "client", "secret")
        with patch(
            "microsoft365_connector.auth.requests.post", side_effect=_fake_post_success
        ) as mock_post:
            authenticator.get_token()
            authenticator.get_token()
        self.assertEqual(mock_post.call_count, 1)

    def test_get_token_raises_on_network_failure(self):
        authenticator = GraphAuthenticator("tenant", "client", "secret")
        with patch("microsoft365_connector.auth.requests.post", side_effect=_fake_post_failure):
            with self.assertRaises(AuthenticationError):
                authenticator.get_token()


if __name__ == "__main__":
    unittest.main()
