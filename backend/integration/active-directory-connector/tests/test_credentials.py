import pytest

from active_directory_connector.credentials import VaultCredentialProvider
from active_directory_connector.exceptions import VaultAccessError


@pytest.mark.asyncio
async def test_get_credentials_reads_vault_once_then_caches(fake_vault_client):
    provider = VaultCredentialProvider(fake_vault_client, "secret/data/active-directory/int-456")

    first = await provider.get_credentials()
    second = await provider.get_credentials()

    assert first.bind_password == "s3cr3t"
    assert second is first
    assert fake_vault_client.read_calls == 1


@pytest.mark.asyncio
async def test_force_refresh_rereads_vault(fake_vault_client):
    provider = VaultCredentialProvider(fake_vault_client, "secret/data/active-directory/int-456")
    await provider.get_credentials()
    await provider.get_credentials(force_refresh=True)

    assert fake_vault_client.read_calls == 2


@pytest.mark.asyncio
async def test_invalidate_forces_rereads_on_next_call(fake_vault_client):
    provider = VaultCredentialProvider(fake_vault_client, "secret/data/active-directory/int-456")
    await provider.get_credentials()
    provider.invalidate()
    await provider.get_credentials()

    assert fake_vault_client.read_calls == 2


@pytest.mark.asyncio
async def test_vault_unreachable_raises_vault_access_error(fake_vault_client):
    fake_vault_client._raise_on_read = ConnectionError("connection refused")
    provider = VaultCredentialProvider(fake_vault_client, "secret/data/active-directory/int-456")

    with pytest.raises(VaultAccessError):
        await provider.get_credentials()


@pytest.mark.asyncio
async def test_missing_bind_password_field_raises(fake_vault_client):
    fake_vault_client._secret = {"lease_duration": 3600}
    provider = VaultCredentialProvider(fake_vault_client, "secret/data/active-directory/int-456")

    with pytest.raises(VaultAccessError):
        await provider.get_credentials()
