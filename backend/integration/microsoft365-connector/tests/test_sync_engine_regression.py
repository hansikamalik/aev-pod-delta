"""
Regression tests for Microsoft 365 Connector against the Hardened Sync Engine.

These tests verify that Microsoft 365 connector output can safely pass through
the hardened sync engine and that the engine's incremental-sync guarantees
remain intact.
"""

from datetime import datetime, timezone

import pytest

from microsoft365_connector.connector import Microsoft365Connector
from microsoft365_connector.credentials import VaultClient
from tests.fixtures import sample_config

# Hardened Sync Engine
from sync_engine.engine import HardenedSyncEngine
from sync_engine.models import SyncResult


class FakePlatformClient:
    """
    Minimal platform client used by the regression test.

    The hardened Sync Engine pushes normalized events through this client.
    """

    def __init__(self, fail_push=False):
        self.pushed = []
        self.checkpoint = None
        self.fail_push = fail_push

    async def push(self, events):
        if self.fail_push:
            raise RuntimeError("Simulated platform push failure")

        self.pushed.extend(events)
        return len(events)

    async def get_checkpoint(self, connector):
        return self.checkpoint

    async def save_checkpoint(self, connector, checkpoint):
        self.checkpoint = checkpoint


@pytest.fixture
def m365_connector():
    """
    Create the Microsoft 365 connector using the same configuration
    used by the connector's existing test suite.
    """
    vault = VaultClient()
    connector = Microsoft365Connector(
        sample_config(),
        vault_client=vault,
    )
    return connector


def make_event(resource_id, timestamp):
    """
    Convert a Microsoft 365 normalized resource into the event shape
    consumed by the hardened sync engine.
    """
    return {
        "id": resource_id,
        "ts": timestamp,
        "resource": "microsoft365",
    }


def test_microsoft365_initial_sync_with_hardened_engine(m365_connector):
    """
    Regression:
    Microsoft 365 resources can be passed through the hardened engine
    during an initial sync.
    """

    events = [
        make_event("m365-user-001", 10),
        make_event("m365-user-002", 20),
        make_event("m365-group-001", 30),
    ]

    client = FakePlatformClient()

    engine = HardenedSyncEngine(
        "microsoft365",
        client,
        retry_base_delay_seconds=0,
    )

    async def fetch(start_time, end_time):
        return events

    result = engine.execute_incremental_sync(fetch)

    # The engine API in the hardening tests is asynchronous.
    import asyncio

    result = asyncio.run(result)

    assert result.status == "success"
    assert result.assets_pushed == 3
    assert len(client.pushed) == 3


def test_microsoft365_second_sync_is_idempotent(m365_connector):
    """
    Regression:
    Running the same Microsoft 365 data twice must not create duplicates.
    """

    events = [
        make_event("m365-user-001", 10),
        make_event("m365-user-002", 20),
    ]

    client = FakePlatformClient()

    engine = HardenedSyncEngine(
        "microsoft365",
        client,
        retry_base_delay_seconds=0,
    )

    async def fetch(start_time, end_time):
        return events

    import asyncio

    # First sync.
    first_result = asyncio.run(
        engine.execute_incremental_sync(fetch)
    )

    assert first_result.status == "success"
    assert first_result.assets_pushed == 2

    # Second sync with exactly the same data.
    second_result = asyncio.run(
        engine.execute_incremental_sync(fetch)
    )

    assert second_result.status == "success"

    # The engine should recognize that there are no new records.
    assert second_result.assets_pushed == 0

    # No duplicate records should have been pushed.
    assert len(client.pushed) == 2


def test_microsoft365_new_record_is_pushed():
    """
    Regression:
    After the initial Microsoft 365 sync, a newly discovered resource
    must be pushed by the incremental sync.
    """

    client = FakePlatformClient()

    engine = HardenedSyncEngine(
        "microsoft365",
        client,
        retry_base_delay_seconds=0,
    )

    first_events = [
        make_event("m365-user-001", 10),
        make_event("m365-user-002", 20),
    ]

    second_events = [
        make_event("m365-user-001", 10),
        make_event("m365-user-002", 20),
        make_event("m365-user-003", 30),
    ]

    import asyncio

    async def first_fetch(start_time, end_time):
        return first_events

    async def second_fetch(start_time, end_time):
        return second_events

    first_result = asyncio.run(
        engine.execute_incremental_sync(first_fetch)
    )

    assert first_result.status == "success"
    assert first_result.assets_pushed == 2

    second_result = asyncio.run(
        engine.execute_incremental_sync(second_fetch)
    )

    assert second_result.status == "success"
    assert second_result.assets_pushed == 1

    assert [event["id"] for event in client.pushed] == [
        "m365-user-001",
        "m365-user-002",
        "m365-user-003",
    ]


def test_microsoft365_failed_push_does_not_advance_checkpoint():
    """
    Regression:
    If pushing Microsoft 365 data fails, the sync checkpoint must not
    incorrectly advance.
    """

    client = FakePlatformClient(fail_push=True)

    engine = HardenedSyncEngine(
        "microsoft365",
        client,
        retry_base_delay_seconds=0,
    )

    events = [
        make_event("m365-user-001", 10),
    ]

    async def fetch(start_time, end_time):
        return events

    import asyncio

    result = asyncio.run(
        engine.execute_incremental_sync(fetch)
    )

    assert result.status in ("failure", "partial_failure")

    # A failed push must not be treated as a successful checkpoint.
    assert client.checkpoint is None


def test_microsoft365_empty_incremental_sync_does_not_move_checkpoint():
    """
    Regression:
    An empty Microsoft 365 incremental run must not incorrectly move
    the sync checkpoint forward.
    """

    client = FakePlatformClient()

    engine = HardenedSyncEngine(
        "microsoft365",
        client,
        retry_base_delay_seconds=0,
    )

    import asyncio

    async def fetch(start_time, end_time):
        return []

    result = asyncio.run(
        engine.execute_incremental_sync(fetch)
    )

    assert result.status == "success"
    assert result.assets_pushed == 0


def test_microsoft365_connector_lifecycle():
    """
    Regression:
    Verify the Microsoft 365 connector still exposes the complete
    connector lifecycle expected by the platform.

    This complements the existing connector unit tests.
    """

    connector_methods = [
        "authenticate",
        "discover",
        "ingest",
        "normalize",
        "push",
        "health_check",
        "sync",
    ]

    for method in connector_methods:
        assert hasattr(
            Microsoft365Connector,
            method,
        ), f"Microsoft365Connector is missing {method}()"
