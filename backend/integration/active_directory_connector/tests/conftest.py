import os
import sys

# ------------------------------------------------------------------
# Ensure the package source is on the path before any imports
# ------------------------------------------------------------------
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.join(_TESTS_DIR, "..", "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

import pytest
from ldap3 import Server
from ldap3.utils.ciDict import CaseInsensitiveDict

# In tests using MOCK_SYNC, ldap3 creates independent in-memory DIT trees
# per Server instance. To allow seed connections and client connections
# targeting the same host to share entries (as a real LDAP server would),
# share DIT by host during test runs.
_shared_dits: dict = {}
_orig_server_init = Server.__init__

def _mock_shared_server_init(self, *args, **kwargs):
    _orig_server_init(self, *args, **kwargs)
    host_key = getattr(self, "host", "").lower()
    if host_key:
        if host_key not in _shared_dits:
            _shared_dits[host_key] = CaseInsensitiveDict()
        self.dit = _shared_dits[host_key]

Server.__init__ = _mock_shared_server_init

@pytest.fixture(autouse=True)
def _reset_mock_dits():
    _shared_dits.clear()
    yield
    _shared_dits.clear()

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
