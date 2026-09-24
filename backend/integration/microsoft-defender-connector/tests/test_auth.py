import httpx
import pytest
import respx

from microsoft_defender_connector.auth import DefenderAuthClient
from microsoft_defender_connector.credentials import VaultCredentialProvider
from microsoft_defender_connector.exceptions import AuthenticationError


@pytest.mark.asyncio
@respx.mock
async def test_get_token_success(defender_config, fake_vault_client):
    token_url = f"{defender_config.login_base_url}{defender_config.tenant_id}/oauth2/token"
    respx.post(token_url).mock(
        return_value=httpx.Response(200, json={"access_token": "abc123", "expires_in": 3600})
    )

    async with httpx.AsyncClient() as http_client:
        provider = VaultCredentialProvider(fake_vault_client, "secret/data/defender/int-123")
        auth = DefenderAuthClient(defender_config, provider, http_client)

        token = await auth.get_token()

        assert token == "abc123"


@pytest.mark.asyncio
@respx.mock
async def test_get_token_caches_until_near_expiry(defender_config, fake_vault_client):
    token_url = f"{defender_config.login_base_url}{defender_config.tenant_id}/oauth2/token"
    route = respx.post(token_url).mock(
        return_value=httpx.Response(200, json={"access_token": "abc123", "expires_in": 3600})
    )

    async with httpx.AsyncClient() as http_client:
        provider = VaultCredentialProvider(fake_vault_client, "secret/data/defender/int-123")
        auth = DefenderAuthClient(defender_config, provider, http_client)

        await auth.get_token()
        await auth.get_token()

        assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_get_token_bad_credentials_raises_and_invalidates_cache(defender_config, fake_vault_client):
    token_url = f"{defender_config.login_base_url}{defender_config.tenant_id}/oauth2/token"
    respx.post(token_url).mock(return_value=httpx.Response(401, text="invalid_client"))

    async with httpx.AsyncClient() as http_client:
        provider = VaultCredentialProvider(fake_vault_client, "secret/data/defender/int-123")
        auth = DefenderAuthClient(defender_config, provider, http_client)

        with pytest.raises(AuthenticationError):
            await auth.get_token()

        # A bad secret should force the next attempt to re-read Vault.
        assert provider._cached is None
