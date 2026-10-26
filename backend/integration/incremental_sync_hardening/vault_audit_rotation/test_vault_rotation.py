import pytest
from connectors.catalog import ALL_21_CONNECTORS
from core.vault_client import VaultClient


@pytest.mark.parametrize("connector_name", list(ALL_21_CONNECTORS.keys()))
def test_all_21_connectors_vault_credential_rotation(connector_name):
    vault = VaultClient()
    initial = vault.get_credentials(connector_name)
    assert initial is not None
    assert "active_token" in initial

    rotated = vault.rotate_credentials(connector_name)
    assert rotated["version"] > initial["version"]
    assert rotated["active_token"] != initial["active_token"]
