from ldap3 import Connection, MOCK_SYNC, Server
import pytest

from active_directory_connector.connector import ActiveDirectoryConnector


def _seed_admin(ldap_server: str, bind_dn: str, password: str) -> None:
    seed_server = Server(ldap_server)
    seed_connection = Connection(seed_server, client_strategy=MOCK_SYNC)
    seed_connection.strategy.add_entry(bind_dn, {"userPassword": password, "sn": "svc-account"})


def make_connector(fake_vault_client) -> ActiveDirectoryConnector:
    return ActiveDirectoryConnector(
        integration_id="int-456",
        credentials_ref="secret/data/active-directory/int-456",
        vault_client=fake_vault_client,
        asset_ingest_url="https://beta.internal/assets/ingest",
        ldap_client_strategy=MOCK_SYNC,
    )


@pytest.mark.asyncio
async def test_health_check_healthy(config_dict, fake_vault_client):
    _seed_admin(config_dict["ldap_server"], config_dict["bind_dn"], "s3cr3t")
    connector = make_connector(fake_vault_client)

    result = await connector.health_check(config_dict)

    assert result["healthy"] is True


@pytest.mark.asyncio
async def test_health_check_vault_unreachable(config_dict, fake_vault_client):
    fake_vault_client._raise_on_read = ConnectionError("connection refused")
    connector = make_connector(fake_vault_client)

    result = await connector.health_check(config_dict)

    assert result["healthy"] is False
    assert result["reason"] == "vault_unreachable"


@pytest.mark.asyncio
async def test_health_check_bind_failure(config_dict, fake_vault_client):
    _seed_admin(config_dict["ldap_server"], config_dict["bind_dn"], "correct-password")
    fake_vault_client._secret = {"bind_password": "wrong-password"}
    connector = make_connector(fake_vault_client)

    result = await connector.health_check(config_dict)

    assert result["healthy"] is False
    assert result["reason"] == "bind_failed"
