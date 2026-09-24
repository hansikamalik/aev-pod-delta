import httpx
import pytest

from microsoft_defender_connector.config import DefenderConfig


@pytest.fixture
def config_dict() -> dict:
    return {
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "client_id": "22222222-2222-2222-2222-222222222222",
        "api_base_url": "https://api.securitycenter.microsoft.com/",
        "login_base_url": "https://login.microsoftonline.com/",
        "poll_interval_minutes": 15,
        "machine_page_size": 500,
        "alert_lookback_hours": 24,
        "request_timeout_seconds": 30.0,
    }


@pytest.fixture
def defender_config(config_dict) -> DefenderConfig:
    return DefenderConfig(**config_dict)


class FakeVaultClient:
    """In-memory stand-in for Alpha's Vault client."""

    def __init__(self, secret: dict | None = None, raise_on_read: Exception | None = None):
        self._secret = secret if secret is not None else {"client_secret": "s3cr3t", "lease_duration": 3600}
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


@pytest.fixture
async def http_client():
    async with httpx.AsyncClient() as client:
        yield client
