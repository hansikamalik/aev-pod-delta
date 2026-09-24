import httpx
import pytest
import respx

from microsoft_defender_connector.connector import MicrosoftDefenderConnector


def make_connector(http_client, fake_vault_client) -> MicrosoftDefenderConnector:
    return MicrosoftDefenderConnector(
        integration_id="int-123",
        credentials_ref="secret/data/defender/int-123",
        vault_client=fake_vault_client,
        asset_ingest_url="https://beta.internal/assets/ingest",
        exposure_ingest_url="https://beta.internal/exposures/ingest",
        http_client=http_client,
    )


@pytest.mark.asyncio
@respx.mock
async def test_discover_yields_normalized_assets(defender_config, config_dict, fake_vault_client):
    token_url = f"{defender_config.login_base_url}{defender_config.tenant_id}/oauth2/token"
    respx.post(token_url).mock(
        return_value=httpx.Response(200, json={"access_token": "abc123", "expires_in": 3600})
    )
    respx.get(f"{defender_config.api_base_url}api/machines").mock(
        return_value=httpx.Response(200, json={"value": [{"id": "m1", "computerDnsName": "host-1"}]})
    )

    async with httpx.AsyncClient() as http_client:
        connector = make_connector(http_client, fake_vault_client)
        assets = [a async for a in connector.discover(config_dict)]

    assert len(assets) == 1
    assert assets[0].external_id == "m1"
    assert assets[0].type == "endpoint"


@pytest.mark.asyncio
@respx.mock
async def test_sync_pull_pushes_assets_and_findings(defender_config, config_dict, fake_vault_client):
    token_url = f"{defender_config.login_base_url}{defender_config.tenant_id}/oauth2/token"
    respx.post(token_url).mock(
        return_value=httpx.Response(200, json={"access_token": "abc123", "expires_in": 3600})
    )
    respx.get(f"{defender_config.api_base_url}api/machines").mock(
        return_value=httpx.Response(200, json={"value": [{"id": "m1", "computerDnsName": "host-1"}]})
    )
    respx.get(f"{defender_config.api_base_url}api/alerts").mock(
        return_value=httpx.Response(
            200,
            json={"value": [{"id": "a1", "machineId": "m1", "severity": "High", "title": "Alert"}]},
        )
    )
    asset_push = respx.post("https://beta.internal/assets/ingest").mock(return_value=httpx.Response(201))
    finding_push = respx.post("https://beta.internal/exposures/ingest").mock(
        return_value=httpx.Response(201)
    )

    async with httpx.AsyncClient() as http_client:
        connector = make_connector(http_client, fake_vault_client)
        result = await connector.sync(config_dict, direction="pull")

    assert result.records_processed == 2
    assert result.records_created == 2
    assert result.records_failed == 0
    assert result.error is None
    assert asset_push.call_count == 1
    assert finding_push.call_count == 1


@pytest.mark.asyncio
async def test_sync_rejects_unsupported_direction(config_dict, fake_vault_client):
    async with httpx.AsyncClient() as http_client:
        connector = make_connector(http_client, fake_vault_client)
        result = await connector.sync(config_dict, direction="push")

    assert result.records_processed == 0
    assert result.error is not None


@pytest.mark.asyncio
@respx.mock
async def test_sync_reports_partial_failure_on_push_error(defender_config, config_dict, fake_vault_client):
    token_url = f"{defender_config.login_base_url}{defender_config.tenant_id}/oauth2/token"
    respx.post(token_url).mock(
        return_value=httpx.Response(200, json={"access_token": "abc123", "expires_in": 3600})
    )
    respx.get(f"{defender_config.api_base_url}api/machines").mock(
        return_value=httpx.Response(200, json={"value": [{"id": "m1", "computerDnsName": "host-1"}]})
    )
    respx.get(f"{defender_config.api_base_url}api/alerts").mock(
        return_value=httpx.Response(200, json={"value": []})
    )
    respx.post("https://beta.internal/assets/ingest").mock(return_value=httpx.Response(500, text="oops"))

    async with httpx.AsyncClient() as http_client:
        connector = make_connector(http_client, fake_vault_client)
        result = await connector.sync(config_dict, direction="pull")

    assert result.records_processed == 1
    assert result.records_created == 0
    assert result.records_failed == 1


def test_config_schema_and_credential_schema_are_valid_shapes(config_dict, fake_vault_client):
    connector = MicrosoftDefenderConnector(
        integration_id="int-123",
        credentials_ref="secret/data/defender/int-123",
        vault_client=fake_vault_client,
        asset_ingest_url="https://beta.internal/assets/ingest",
        exposure_ingest_url="https://beta.internal/exposures/ingest",
    )

    config_schema = connector.config_schema()
    credential_schema = connector.credential_schema()

    assert config_schema["required"] == ["tenant_id", "client_id"]
    assert credential_schema["required"] == ["client_secret"]
