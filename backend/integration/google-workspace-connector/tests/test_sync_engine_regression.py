from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from google_workspace_connector.connector import GoogleWorkspaceConnector
from google_workspace_connector.state import InMemorySyncStateStore

from sync_engine.engine import HardenedSyncEngine
from sync_engine.models import Checkpoint


class FakeAuth:
    def credentials(self, config, credentials):
        return "authorized"


class FakeRequest:
    def __init__(self, response):
        self.response = response

    def execute(self):
        return self.response


class FakeActivities:
    def __init__(self, events):
        self.events = events

    def list(self, **kwargs):
        return FakeRequest(
            {
                "items": self.events,
                "nextPageToken": None,
            }
        )


class FakeReports:
    def __init__(self, events):
        self._events = events

    def activities(self):
        return FakeActivities(self._events)


class FakeClients:
    def __init__(self, credentials, events):
        self.reports = FakeReports(events)


class FakePlatformClient:
    def __init__(self):
        self.checkpoint = None
        self.pushed_assets = []

    def get_checkpoint(self, connector_id):
        return self.checkpoint

    def push_assets(self, assets):
        self.pushed_assets.extend(assets)

    def save_checkpoint(self, checkpoint):
        self.checkpoint = checkpoint


@pytest.fixture
def config():
    return {
        "customer_id": "my_customer",
        "domain": "example.com",
        "admin_user": "admin@example.com",
        "_credentials": {
            "service_account": {
                "client_email": "svc@example.com",
                "private_key_ref": "vault://google-workspace/service-account",
            }
        },
        "sync": {
            "users": False,
            "audit_logs": True,
            "audit_application": "login",
        },
    }


def make_event(
    event_time="2026-01-01T00:00:00Z",
    email="alice@example.com",
    event_name="login_success",
):
    return {
        "id": {
            "time": event_time,
            "applicationName": "login",
        },
        "actor": {
            "email": email,
        },
        "events": [
            {
                "name": event_name,
            }
        ],
    }


@pytest.fixture
def google_connector(config):
    events = [
        make_event(),
    ]

    def client_factory(credentials):
        return FakeClients(credentials, events)

    return GoogleWorkspaceConnector(
        FakeAuth(),
        InMemorySyncStateStore(),
        client_factory=client_factory,
    )


@pytest.mark.asyncio
async def test_google_workspace_initial_sync(google_connector):
    platform = FakePlatformClient()

    engine = HardenedSyncEngine(
        "google_workspace",
        platform,
        retry_base_delay_seconds=0,
    )

    async def fetch():
        return [
            event
            async for event in google_connector.ingest(
                {
                    **{
                        "customer_id": "my_customer",
                        "domain": "example.com",
                        "admin_user": "admin@example.com",
                        "_credentials": {
                            "service_account": {
                                "client_email": "svc@example.com",
                                "private_key_ref": "vault://google-workspace/service-account",
                            }
                        },
                        "sync": {
                            "users": False,
                            "audit_logs": True,
                            "audit_application": "login",
                        },
                    }
                }
            )
        ]

    result = await engine.execute_incremental_sync(fetch)

    assert result.status == "success"
    assert result.assets_discovered == 1
    assert result.assets_pushed == 1
    assert len(platform.pushed_assets) == 1
    assert platform.checkpoint is not None


@pytest.mark.asyncio
async def test_google_workspace_second_sync_is_idempotent(
    google_connector,
):
    platform = FakePlatformClient()

    engine = HardenedSyncEngine(
        "google_workspace",
        platform,
        retry_base_delay_seconds=0,
    )

    async def fetch():
        return [
            event
            async for event in google_connector.ingest(
                {
                    "customer_id": "my_customer",
                    "domain": "example.com",
                    "admin_user": "admin@example.com",
                    "_credentials": {
                        "service_account": {
                            "client_email": "svc@example.com",
                            "private_key_ref": "vault://google-workspace/service-account",
                        }
                    },
                    "sync": {
                        "users": False,
                        "audit_logs": True,
                        "audit_application": "login",
                    },
                }
            )
        ]

    first = await engine.execute_incremental_sync(fetch)

    assert first.status == "success"
    assert first.assets_pushed == 1

    second = await engine.execute_incremental_sync(fetch)

    assert second.status == "success"
    assert second.assets_pushed == 0
    assert second.assets_skipped == 1
    assert len(platform.pushed_assets) == 1


@pytest.mark.asyncio
async def test_google_workspace_new_event_is_pushed_incrementally(
    config,
):
    events = [
        make_event(),
    ]

    def client_factory(credentials):
        return FakeClients(credentials, events)

    connector = GoogleWorkspaceConnector(
        FakeAuth(),
        InMemorySyncStateStore(),
        client_factory=client_factory,
    )

    platform = FakePlatformClient()

    engine = HardenedSyncEngine(
        "google_workspace",
        platform,
        retry_base_delay_seconds=0,
    )

    async def fetch():
        return [
            event
            async for event in connector.ingest(config)
        ]

    first = await engine.execute_incremental_sync(fetch)

    assert first.assets_pushed == 1

    events.append(
        make_event(
            event_time="2026-01-01T01:00:00Z",
            email="bob@example.com",
            event_name="login_success",
        )
    )

    second = await engine.execute_incremental_sync(fetch)

    assert second.status == "success"
    assert second.assets_pushed == 1
    assert len(platform.pushed_assets) == 2


@pytest.mark.asyncio
async def test_google_workspace_duplicate_events_are_deduplicated(
    config,
):
    duplicate = make_event()

    events = [
        duplicate,
        duplicate.copy(),
    ]

    def client_factory(credentials):
        return FakeClients(credentials, events)

    connector = GoogleWorkspaceConnector(
        FakeAuth(),
        InMemorySyncStateStore(),
        client_factory=client_factory,
    )

    platform = FakePlatformClient()

    engine = HardenedSyncEngine(
        "google_workspace",
        platform,
        retry_base_delay_seconds=0,
    )

    async def fetch():
        return [
            event
            async for event in connector.ingest(config)
        ]

    result = await engine.execute_incremental_sync(fetch)

    assert result.status == "success"
    assert result.assets_discovered == 2
    assert result.assets_pushed == 1
    assert len(platform.pushed_assets) == 1


@pytest.mark.asyncio
async def test_google_workspace_empty_sync(config):
    events = []

    def client_factory(credentials):
        return FakeClients(credentials, events)

    connector = GoogleWorkspaceConnector(
        FakeAuth(),
        InMemorySyncStateStore(),
        client_factory=client_factory,
    )

    platform = FakePlatformClient()

    engine = HardenedSyncEngine(
        "google_workspace",
        platform,
        retry_base_delay_seconds=0,
    )

    async def fetch():
        return [
            event
            async for event in connector.ingest(config)
        ]

    result = await engine.execute_incremental_sync(fetch)

    assert result.status == "success"
    assert result.assets_discovered == 0
    assert result.assets_pushed == 0
    assert len(platform.pushed_assets) == 0


@pytest.mark.asyncio
async def test_google_workspace_push_failure_preserves_checkpoint(
    config,
):
    events = [make_event()]

    def client_factory(credentials):
        return FakeClients(credentials, events)

    connector = GoogleWorkspaceConnector(
        FakeAuth(),
        InMemorySyncStateStore(),
        client_factory=client_factory,
    )

    platform = MagicMock()
    platform.get_checkpoint.return_value = None
    platform.push_assets.side_effect = RuntimeError("platform push failed")

    engine = HardenedSyncEngine(
        "google_workspace",
        platform,
        retry_base_delay_seconds=0,
    )

    async def fetch():
        return [
            event
            async for event in connector.ingest(config)
        ]

    result = await engine.execute_incremental_sync(fetch)

    assert result.status == "partial_failure"
    assert result.assets_pushed == 0
    platform.save_checkpoint.assert_not_called()
