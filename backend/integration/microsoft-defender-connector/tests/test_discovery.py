import httpx
import pytest
import respx

from microsoft_defender_connector.auth import DefenderAuthClient
from microsoft_defender_connector.credentials import VaultCredentialProvider
from microsoft_defender_connector.discovery import iter_machines


@pytest.mark.asyncio
@respx.mock
async def test_iter_machines_follows_pagination(defender_config, fake_vault_client):
    token_url = f"{defender_config.login_base_url}{defender_config.tenant_id}/oauth2/token"
    respx.post(token_url).mock(
        return_value=httpx.Response(200, json={"access_token": "abc123", "expires_in": 3600})
    )

    machines_url = f"{defender_config.api_base_url}api/machines"
    next_url = f"{machines_url}?$top=500&$skip=500"

    respx.get(machines_url).mock(
        return_value=httpx.Response(
            200,
            json={
                "value": [{"id": "m1", "computerDnsName": "host-1"}],
                "@odata.nextLink": next_url,
            },
        )
    )
    respx.get(next_url).mock(
        return_value=httpx.Response(200, json={"value": [{"id": "m2", "computerDnsName": "host-2"}]})
    )

    async with httpx.AsyncClient() as http_client:
        provider = VaultCredentialProvider(fake_vault_client, "secret/data/defender/int-123")
        auth = DefenderAuthClient(defender_config, provider, http_client)

        machines = [m async for m in iter_machines(defender_config, auth, http_client)]

    assert [m["id"] for m in machines] == ["m1", "m2"]
