import pytest
from unittest.mock import MagicMock, AsyncMock

from sync_engine.engine import HardenedSyncEngine


@pytest.fixture
def mock_platform_client():
    client = MagicMock()
    client.get_checkpoint.return_value = None
    client.push_assets.return_value = None
    client.save_checkpoint.return_value = None
    return client


@pytest.mark.asyncio
async def test_initial_sync_without_checkpoint(mock_platform_client):
    engine = HardenedSyncEngine(
        connector_id="splunk_test",
        platform_client=mock_platform_client,
        lookback_buffer_seconds=60
    )

    fetch_events_fn = AsyncMock(return_value=[
        {
            "id": "event-001",
            "name": "User Login Failed",
            "timestamp": "2026-09-24T12:00:00+00:00",
            "host": "sec-srv-01",
            "password": "super-secret-password"
        }
    ])

    result = await engine.execute_incremental_sync(fetch_events_fn, default_lookback_days=7)

    assert result.status == "success"
    assert result.assets_discovered == 1
    assert result.assets_pushed == 1
    assert len(result.errors) == 0

    pushed_asset = mock_platform_client.push_assets.call_args[0][0][0]
    assert pushed_asset.id == "event-001"
    assert "password" not in pushed_asset.raw


@pytest.mark.asyncio
async def test_event_deduplication(mock_platform_client):
    engine = HardenedSyncEngine(
        connector_id="splunk_test",
        platform_client=mock_platform_client
    )

    duplicate_events = [
        {"id": "evt-1", "name": "Event 1", "timestamp": "2026-09-24T12:00:00Z"},
        {"id": "evt-1", "name": "Event 1 Duplicate", "timestamp": "2026-09-24T12:00:00Z"},
        {"id": "evt-2", "name": "Event 2", "timestamp": "2026-09-24T12:01:00Z"}
    ]

    fetch_events_fn = AsyncMock(return_value=duplicate_events)

    result = await engine.execute_incremental_sync(fetch_events_fn)

    assert result.status == "success"
    assert result.assets_discovered == 3
    assert result.assets_pushed == 2

@pytest.mark.asyncio
async def test_sync_resumes_after_engine_restart():
    from regression_tests.mock_platform import MockPlatformClient

    platform = MockPlatformClient()
    connector_id = "dr_test_connector"

    first_engine = HardenedSyncEngine(
        connector_id=connector_id,
        platform_client=platform,
        lookback_buffer_seconds=0,
        retry_base_delay_seconds=0,
    )

    first_fetch = AsyncMock(return_value=[
        {
            "id": "dr-event-001",
            "name": "Initial Event",
            "timestamp": "2026-09-24T12:00:00+00:00",
        }
    ])

    first_result = await first_engine.execute_incremental_sync(
        first_fetch
    )

    assert first_result.status == "success"
    assert platform.get_checkpoint(connector_id) is not None

    saved_checkpoint = platform.get_checkpoint(connector_id)

    # Simulate an engine restart while preserving platform checkpoint storage.
    restarted_engine = HardenedSyncEngine(
        connector_id=connector_id,
        platform_client=platform,
        lookback_buffer_seconds=0,
        retry_base_delay_seconds=0,
    )

    second_fetch = AsyncMock(return_value=[])

    second_result = await restarted_engine.execute_incremental_sync(
        second_fetch
    )

    assert second_result.status == "success"
    assert second_result.mode == "incremental"
    assert second_fetch.await_count == 1

    fetch_start_time = second_fetch.await_args.args[0]

    from datetime import datetime

    actual_start = datetime.fromisoformat(fetch_start_time)

    assert actual_start == saved_checkpoint.high_water_mark
    assert platform.get_checkpoint(connector_id) is not None
