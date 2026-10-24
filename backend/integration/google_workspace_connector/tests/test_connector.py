from __future__ import annotations

import pytest

from google_workspace_connector.connector import GoogleWorkspaceConnector
from google_workspace_connector.state import InMemorySyncStateStore


class FakeAuth:
    def credentials(self, config, credentials):
        return "authorized"


class FakeRequest:
    def __init__(self, response):
        self.response = response

    def execute(self):
        return self.response


class FakeUsers:
    def list(self, **kwargs):
        return FakeRequest(
            {
                "users": [
                    {
                        "id": "u-1",
                        "primaryEmail": "alice@example.com",
                        "name": {"fullName": "Alice"},
                    }
                ],
                "nextPageToken": None,
            }
        )


class FakeDirectory:
    def users(self):
        return FakeUsers()


class FakeActivities:
    def list(self, **kwargs):
        return FakeRequest(
            {
                "items": [
                    {
                        "id": {"time": "2026-01-01T00:00:00Z", "applicationName": "login"},
                        "actor": {"email": "alice@example.com"},
                        "events": [{"name": "login_success"}],
                    }
                ],
                "nextPageToken": None,
            }
        )


class FakeReports:
    def activities(self):
        return FakeActivities()


class FakeClients:
    def __init__(self, credentials):
        self.directory = FakeDirectory()
        self.reports = FakeReports()


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
        "sync": {"users": True, "audit_logs": True},
    }


@pytest.mark.asyncio
async def test_discover(config):
    connector = GoogleWorkspaceConnector(
        FakeAuth(), InMemorySyncStateStore(), client_factory=FakeClients
    )
    assets = [asset async for asset in connector.discover(config)]
    assert len(assets) == 1
    assert assets[0].external_id == "u-1"


@pytest.mark.asyncio
async def test_ingest(config):
    connector = GoogleWorkspaceConnector(
        FakeAuth(), InMemorySyncStateStore(), client_factory=FakeClients
    )
    events = [event async for event in connector.ingest(config)]
    assert len(events) == 1
    assert events[0]["type"] == "google_workspace_audit_event"


@pytest.mark.asyncio
async def test_sync(config):
    connector = GoogleWorkspaceConnector(
        FakeAuth(), InMemorySyncStateStore(), client_factory=FakeClients
    )
    result = await connector.sync(config, "pull")
    assert result.records_processed == 2
    assert result.records_failed == 0


@pytest.mark.asyncio
async def test_health_check(config):
    connector = GoogleWorkspaceConnector(
        FakeAuth(), InMemorySyncStateStore(), client_factory=FakeClients
    )
    result = await connector.health_check(config)
    assert result["healthy"] is True
