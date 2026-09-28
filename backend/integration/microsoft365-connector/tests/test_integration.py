import unittest
from unittest.mock import MagicMock, patch

from microsoft365_connector.connector import Microsoft365Connector
from microsoft365_connector.credentials import VaultClient
from tests.fixtures import sample_config
from tests.sandbox.mock_graph_api import FakeGraphSession


def _fake_token_post(*args, **kwargs):
    class R:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"access_token": "fake-graph-token", "expires_in": 3600}

    return R()


class TestIntegration(unittest.TestCase):
    def test_run_sync_end_to_end(self):
        vault = MagicMock(spec=VaultClient)
        vault.get_secret.side_effect = [
            {"client_secret": "shh"},
            {"api_token": "platform-token"},
        ]

        connector = Microsoft365Connector(sample_config(), vault_client=vault)

        fake_platform_session = MagicMock()
        fake_platform_session.post.return_value.raise_for_status.return_value = None

        with patch("microsoft365_connector.auth.requests.post", side_effect=_fake_token_post):
            connector.authenticate()

        connector._discovery.session = FakeGraphSession()
        connector._platform.session = fake_platform_session

        result = connector.sync()

        # 2 users + 1 group + 1 device + 1 domain + 1 license = 6 assets
        self.assertEqual(result["push_result"]["assets"]["total"], 6)
        self.assertEqual(result["push_result"]["assets"]["pushed"], 6)
        # 1 directory audit log entry = 1 finding
        self.assertEqual(result["push_result"]["findings"]["total"], 1)
        self.assertEqual(result["push_result"]["findings"]["pushed"], 1)
        self.assertEqual(result["health"]["graph_api"], "ok")
        self.assertEqual(result["health"]["platform_api"], "ok")

    def test_run_sync_acceptance_m365_users_synced(self):
        """
        Acceptance check: M365 users sync end-to-end (auth -> discover ->
        normalize -> push) regardless of what else is enabled.
        """
        vault = MagicMock(spec=VaultClient)
        vault.get_secret.side_effect = [
            {"client_secret": "shh"},
            {"api_token": "platform-token"},
        ]

        config = sample_config()
        config.discover_resources = {
            "user": True,
            "group": False,
            "device": False,
            "domain": False,
            "license": False,
            "audit_log": False,
        }
        connector = Microsoft365Connector(config, vault_client=vault)

        fake_platform_session = MagicMock()
        fake_platform_session.post.return_value.raise_for_status.return_value = None

        with patch("microsoft365_connector.auth.requests.post", side_effect=_fake_token_post):
            connector.authenticate()

        connector._discovery.session = FakeGraphSession()
        connector._platform.session = fake_platform_session

        result = connector.sync()

        self.assertEqual(result["push_result"]["assets"]["total"], 2)  # u-1, u-2
        self.assertEqual(result["push_result"]["assets"]["pushed"], 2)
        self.assertEqual(result["push_result"]["findings"]["total"], 0)


if __name__ == "__main__":
    unittest.main()
