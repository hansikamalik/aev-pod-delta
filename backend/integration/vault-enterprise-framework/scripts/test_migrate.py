import pytest
from unittest.mock import patch
from requests.exceptions import HTTPError

from migrate_cyberark_to_vault import CyberArkToVaultMigrator, CYBERARK_PVWA_URL, VAULT_KV_MOUNT


@pytest.fixture
def migrator():
    with patch("migrate_cyberark_to_vault.hvac.Client") as mock_hvac:
        instance = CyberArkToVaultMigrator()
        instance.vault_client = mock_hvac.return_value
        yield instance


class TestCyberArkToVaultMigrator:

    def test_cyberark_login_success(self, migrator, requests_mock):
        login_url = f"{CYBERARK_PVWA_URL}/api/auth/Logon"
        requests_mock.post(login_url, text='"mocked_cyberark_token_123"')

        migrator.cyberark_login()

        assert migrator.cyberark_token == "mocked_cyberark_token_123"
        assert migrator.session.headers.get("Authorization") == "mocked_cyberark_token_123"

    def test_migrate_safe_full_success(self, migrator, requests_mock):
        safe_name = "Linux-Enterprise-Safe"
        accounts_url = f"{CYBERARK_PVWA_URL}/api/Accounts?filter=safeName eq {safe_name}"
        requests_mock.get(
            accounts_url,
            json={"value": [{"id": "101_1", "userName": "root", "address": "srv-db01.local", "platformId": "UnixSSH"}]}
        )

        password_url = f"{CYBERARK_PVWA_URL}/api/Accounts/101_1/Password/Retrieve"
        requests_mock.post(password_url, text='"SuperSecretPass123!"')

        stats = migrator.migrate_safe(safe_name)

        assert stats == {"success": 1, "failed": 0}
        migrator.vault_client.secrets.kv.v2.create_or_update_secret.assert_called_once_with(
            mount_point=VAULT_KV_MOUNT,
            path="cyberark_migrated/linux-enterprise-safe/srv-db01.local/root",
            secret={
                "username": "root",
                "password": "SuperSecretPass123!",
                "address": "srv-db01.local",
                "platform_id": "UnixSSH",
                "cyberark_account_id": "101_1",
                "origin_safe": safe_name
            }
        )
