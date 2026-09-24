import pytest

from active_directory_connector.config import ActiveDirectoryConfig


@pytest.fixture
def config_dict() -> dict:
    return {
        "ldap_server": "dc01.corp.example.com",
        "ldap_port": 636,
        "use_ssl": True,
        "bind_dn": "CN=svc-aev-sync,OU=Service Accounts,DC=corp,DC=example,DC=com",
        "base_dn": "DC=corp,DC=example,DC=com",
        "user_search_base": "OU=Users,DC=corp,DC=example,DC=com",
        "group_search_base": "OU=Groups,DC=corp,DC=example,DC=com",
        "sync_groups": True,
        "page_size": 500,
        "connect_timeout_seconds": 10.0,
        "receive_timeout_seconds": 30.0,
    }


@pytest.fixture
def ad_config(config_dict) -> ActiveDirectoryConfig:
    return ActiveDirectoryConfig(**config_dict)


class FakeVaultClient:
    """In-memory stand-in for Alpha's Vault client."""

    def __init__(self, secret: dict | None = None, raise_on_read: Exception | None = None):
        self._secret = secret if secret is not None else {
            "bind_password": "s3cr3t",
            "lease_duration": 3600,
        }
        self._raise_on_read = raise_on_read
        self.read_calls = 0

    async def read_secret(self, path: str) -> dict:
        self.read_calls += 1
        if self._raise_on_read:
            raise self._raise_on_read
        return self._secret


@pytest.fixture
def fake_vault_client() -> FakeVaultClient:
    return FakeVaultClient()
