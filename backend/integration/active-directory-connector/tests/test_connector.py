"""
Connector-level tests patch discovery.iter_users / iter_groups directly
(they're already covered against a fake LDAP connection in
test_discovery.py) so these tests focus purely on sync()'s
orchestration: pushing normalized records and building a SyncResult.
"""

import httpx
import pytest
import respx

from active_directory_connector.connector import ActiveDirectoryConnector

USER_ENTRY = {
    "dn": "CN=Jane Doe,OU=Users,DC=corp,DC=example,DC=com",
    "attributes": {
        "objectGUID": "guid-user-1",
        "sAMAccountName": "jdoe",
        "displayName": "Jane Doe",
        "mail": "jdoe@corp.example.com",
        "userAccountControl": "512",
        "memberOf": [],
    },
}

GROUP_ENTRY = {
    "dn": "CN=Engineering,OU=Groups,DC=corp,DC=example,DC=com",
    "attributes": {"objectGUID": "guid-group-1", "cn": "Engineering", "member": ["CN=Jane Doe"]},
}


async def _fake_iter_users(cfg, auth):
    yield USER_ENTRY


async def _fake_iter_groups(cfg, auth):
    yield GROUP_ENTRY


async def _fake_iter_users_empty(cfg, auth):
    return
    yield  # pragma: no cover


def make_connector(http_client, fake_vault_client) -> ActiveDirectoryConnector:
    return ActiveDirectoryConnector(
        integration_id="int-456",
        credentials_ref="secret/data/active-directory/int-456",
        vault_client=fake_vault_client,
        asset_ingest_url="https://beta.internal/assets/ingest",
        http_client=http_client,
    )


@pytest.mark.asyncio
async def test_discover_yields_normalized_user_and_group_assets(
    monkeypatch, config_dict, fake_vault_client
):
    monkeypatch.setattr("active_directory_connector.connector.iter_users", _fake_iter_users)
    monkeypatch.setattr("active_directory_connector.connector.iter_groups", _fake_iter_groups)

    async with httpx.AsyncClient() as http_client:
        connector = make_connector(http_client, fake_vault_client)
        assets = [a async for a in connector.discover(config_dict)]

    types = {a.type for a in assets}
    assert types == {"ad_user", "ad_group"}


@pytest.mark.asyncio
async def test_discover_skips_groups_when_sync_groups_false(
    monkeypatch, config_dict, fake_vault_client
):
    monkeypatch.setattr("active_directory_connector.connector.iter_users", _fake_iter_users)
    monkeypatch.setattr("active_directory_connector.connector.iter_groups", _fake_iter_groups)
    config_dict["sync_groups"] = False

    async with httpx.AsyncClient() as http_client:
        connector = make_connector(http_client, fake_vault_client)
        assets = [a async for a in connector.discover(config_dict)]

    assert {a.type for a in assets} == {"ad_user"}


@pytest.mark.asyncio
@respx.mock
async def test_sync_pull_pushes_users_and_groups(monkeypatch, config_dict, fake_vault_client):
    monkeypatch.setattr("active_directory_connector.connector.iter_users", _fake_iter_users)
    monkeypatch.setattr("active_directory_connector.connector.iter_groups", _fake_iter_groups)
    asset_push = respx.post("https://beta.internal/assets/ingest").mock(return_value=httpx.Response(201))

    async with httpx.AsyncClient() as http_client:
        connector = make_connector(http_client, fake_vault_client)
        result = await connector.sync(config_dict, direction="pull")

    assert result.records_processed == 2
    assert result.records_created == 2
    assert result.records_failed == 0
    assert result.error is None
    assert asset_push.call_count == 2


@pytest.mark.asyncio
async def test_sync_rejects_unsupported_direction(config_dict, fake_vault_client):
    async with httpx.AsyncClient() as http_client:
        connector = make_connector(http_client, fake_vault_client)
        result = await connector.sync(config_dict, direction="push")

    assert result.records_processed == 0
    assert result.error is not None


@pytest.mark.asyncio
@respx.mock
async def test_sync_reports_partial_failure_on_push_error(monkeypatch, config_dict, fake_vault_client):
    monkeypatch.setattr("active_directory_connector.connector.iter_users", _fake_iter_users)
    monkeypatch.setattr("active_directory_connector.connector.iter_groups", _fake_iter_groups)
    respx.post("https://beta.internal/assets/ingest").mock(return_value=httpx.Response(500, text="oops"))

    async with httpx.AsyncClient() as http_client:
        connector = make_connector(http_client, fake_vault_client)
        result = await connector.sync(config_dict, direction="pull")

    assert result.records_processed == 2
    assert result.records_created == 0
    assert result.records_failed == 2


@pytest.mark.asyncio
async def test_ingest_yields_nothing(config_dict, fake_vault_client):
    async with httpx.AsyncClient() as http_client:
        connector = make_connector(http_client, fake_vault_client)
        findings = [f async for f in connector.ingest(config_dict)]

    assert findings == []


def test_config_schema_and_credential_schema_are_valid_shapes(fake_vault_client):
    connector = ActiveDirectoryConnector(
        integration_id="int-456",
        credentials_ref="secret/data/active-directory/int-456",
        vault_client=fake_vault_client,
        asset_ingest_url="https://beta.internal/assets/ingest",
    )

    config_schema = connector.config_schema()
    credential_schema = connector.credential_schema()

    assert config_schema["required"] == ["ldap_server", "bind_dn", "base_dn"]
    assert credential_schema["required"] == ["bind_password"]
