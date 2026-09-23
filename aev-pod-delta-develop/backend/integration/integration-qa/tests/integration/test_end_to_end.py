"""
End-to-end integration suite — Day 6/7 material (contract_v2 aligned).

Flow under test (per the week plan demo + §2 lifecycle):
    Vault -> Credentials -> Connector -> discover -> ingest -> SyncResult
    Cron -> Sync job -> Distributed lock -> Connector execution

Runs against the dummy connector by default (always green); real connectors
join as they land. Run:  pytest tests/integration -m integration
"""
from __future__ import annotations

import asyncio

import pytest

from qa.mocks.mock_vault import seeded_vault
from qa.validators import validate_assets
from tests.conftest import module_or_skip


def _sync(connector):
    return asyncio.run(connector.sync())


@pytest.mark.integration
def test_vault_to_credentials_to_connector(dummy_connector, vault, vault_config):
    """Vault -> credentials -> connector -> healthy (§17)."""
    creds = vault.get_secret("dummy/api_key")
    assert creds == vault_config["dummy"]
    dummy_connector._apply_credentials(creds)
    assert dummy_connector.check_health() is True


@pytest.mark.integration
def test_full_sync_pipeline(dummy_connector, vault):
    """§2/§13/§14: discover -> ingest -> SyncResult, end to end."""
    dummy_connector._apply_credentials(vault.get_secret("dummy/api_key"))
    result = _sync(dummy_connector)
    assert result.connector == "dummy"
    assert result.status == "success"
    assert result.assets_discovered == 2
    assert result.assets_pushed == 2
    assert result.errors == []
    assert len(dummy_connector.platform) == 2
    assert not validate_assets(dummy_connector.platform)


@pytest.mark.integration
def test_scheduled_sync_respects_lock():
    """Cron job + distributed lock: two concurrent syncs, only one executes."""
    lock = module_or_skip("lock")
    store, executions = {}, []
    with lock.acquire(store, "sync-job"):
        if lock.try_acquire(store, "sync-job"):
            executions.append("second-run")  # must NOT happen
    assert "second-run" not in executions


@pytest.mark.integration
def test_real_azure_pipeline_when_available(vault):
    """Lights up once Bhavesh/Subramani/Ashwin modules are merged (§2 flow)."""
    auth = module_or_skip("azure.auth")
    discovery = module_or_skip("azure.discovery")
    normalize = module_or_skip("azure.normalize")

    token = auth.authenticate(vault.get_secret("azure/service_principal"))
    raw = discovery.discover_all(token=token)
    assets = normalize.normalize_batch("vm", raw.get("vm", []))
    assert not validate_assets(assets)
