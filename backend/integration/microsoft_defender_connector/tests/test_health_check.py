import httpx
import pytest
import respx

from microsoft_defender_connector.connector import MicrosoftDefenderConnector


@pytest.mark.asyncio
@respx.mock
async def test_health_check_healthy(defender_config, config_dict, fake_vault_client):
    token_url = f"{defender_config.login_base_url}{defender_config.tenant_id}/oauth2/token"
    respx.post(token_url).mock(
        return_value=httpx.Response(200, json={"access_token": "abc123", "expires_in": 3600})
    )
    respx.get(f"{defender_config.api_base_url}api/machines").mock(
        return_value=httpx.Response(200, json={"value": []})
    )

    async with httpx.AsyncClient() as http_client:
        connector = MicrosoftDefenderConnector(
            integration_id="int-123",
            credentials_ref="secret/data/defender/int-123",
            vault_client=fake_vault_client,
            asset_ingest_url="https://beta.internal/assets/ingest",
            exposure_ingest_url="https://beta.internal/exposures/ingest",
            http_client=http_client,
        )

        result = await connector.health_check(config_dict)

    assert result["healthy"] is True


@pytest.mark.asyncio
@respx.mock
async def test_health_check_vault_unreachable(defender_config, config_dict, fake_vault_client):
    fake_vault_client._raise_on_read = ConnectionError("connection refused")

    async with httpx.AsyncClient() as http_client:
        connector = MicrosoftDefenderConnector(
            integration_id="int-123",
            credentials_ref="secret/data/defender/int-123",
            vault_client=fake_vault_client,
            asset_ingest_url="https://beta.internal/assets/ingest",
            exposure_ingest_url="https://beta.internal/exposures/ingest",
            http_client=http_client,
        )

        result = await connector.health_check(config_dict)

    assert result["healthy"] is False
    assert result["reason"] == "vault_unreachable"


@pytest.mark.asyncio
@respx.mock
async def test_health_check_auth_failure(defender_config, config_dict, fake_vault_client):
    token_url = f"{defender_config.login_base_url}{defender_config.tenant_id}/oauth2/token"
    respx.post(token_url).mock(return_value=httpx.Response(401, text="invalid_client"))

    async with httpx.AsyncClient() as http_client:
        connector = MicrosoftDefenderConnector(
            integration_id="int-123",
            credentials_ref="secret/data/defender/int-123",
            vault_client=fake_vault_client,
            asset_ingest_url="https://beta.internal/assets/ingest",
            exposure_ingest_url="https://beta.internal/exposures/ingest",
            http_client=http_client,
        )

        result = await connector.health_check(config_dict)

    assert result["healthy"] is False
    assert result["reason"] == "auth_failed"
