import pytest
from ldap3 import MOCK_SYNC

from active_directory_connector.auth import ADAuthClient
from active_directory_connector.credentials import VaultCredentialProvider
from active_directory_connector.exceptions import LDAPBindError


def _seed_admin(connection, bind_dn: str, password: str) -> None:
    """ldap3's MOCK_SYNC strategy needs the bind identity to exist as an
    entry with a matching userPassword before Connection.bind() will
    succeed."""
    connection.strategy.add_entry(bind_dn, {"userPassword": password, "sn": "svc-account"})


@pytest.mark.asyncio
async def test_get_connection_binds_successfully(ad_config, fake_vault_client):
    provider = VaultCredentialProvider(fake_vault_client, "secret/data/active-directory/int-456")
    auth = ADAuthClient(ad_config, provider, client_strategy=MOCK_SYNC)

    # Seed the mock server's directory with the bind identity before binding.
    # We reach in via a throwaway connection since the mock server state is
    # shared across Connection objects created against the same Server.
    from ldap3 import Connection, Server

    seed_server = Server(ad_config.ldap_server)
    seed_connection = Connection(seed_server, client_strategy=MOCK_SYNC)
    _seed_admin(seed_connection, ad_config.bind_dn, "s3cr3t")

    connection = await auth.get_connection()

    assert connection.bound is True


@pytest.mark.asyncio
async def test_get_connection_caches_bound_connection(ad_config, fake_vault_client):
    from ldap3 import Connection, Server

    provider = VaultCredentialProvider(fake_vault_client, "secret/data/active-directory/int-456")
    auth = ADAuthClient(ad_config, provider, client_strategy=MOCK_SYNC)

    seed_server = Server(ad_config.ldap_server)
    seed_connection = Connection(seed_server, client_strategy=MOCK_SYNC)
    _seed_admin(seed_connection, ad_config.bind_dn, "s3cr3t")

    first = await auth.get_connection()
    second = await auth.get_connection()

    assert first is second


@pytest.mark.asyncio
async def test_get_connection_bad_password_raises_and_invalidates_cache(ad_config, fake_vault_client):
    from ldap3 import Connection, Server

    fake_vault_client._secret = {"bind_password": "wrong-password"}
    provider = VaultCredentialProvider(fake_vault_client, "secret/data/active-directory/int-456")
    auth = ADAuthClient(ad_config, provider, client_strategy=MOCK_SYNC)

    seed_server = Server(ad_config.ldap_server)
    seed_connection = Connection(seed_server, client_strategy=MOCK_SYNC)
    _seed_admin(seed_connection, ad_config.bind_dn, "s3cr3t")  # real password differs

    with pytest.raises(LDAPBindError):
        await auth.get_connection()

    assert provider._cached is None
