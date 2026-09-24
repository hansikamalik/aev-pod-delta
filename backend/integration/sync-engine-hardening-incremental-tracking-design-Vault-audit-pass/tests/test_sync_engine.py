import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock

from sync_engine.engine import HardenedSyncEngine
from sync_engine.models import Checkpoint


@pytest.fixture
def mock_platform_client():
    client = MagicMock()
    client.get_checkpoint.return_value = None
    client.push_assets.return_value = None
    client.save_checkpoint.return_value = None
    return client


@pytest.mark.asyncio
async def test_initial_sync_without_checkpoint(mock_platform_client):
    """Verifies that an initial sync calculates start time based on default_lookback_days."""
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
            "password": "super-secret-password"  # Should be redacted
        }
    ])

    result = await engine.execute_incremental_sync(fetch_events_fn, default_lookback_days=7)

    assert result.status == "success"
    assert result.assets_discovered == 1
    assert result.assets_pushed == 1
    assert len(result.errors) == 0

    # Verify platform client interactions
    mock_platform_client.get_checkpoint.assert_called_once_with("splunk_test")
    mock_platform_client.push_assets.assert_called_once()
    mock_platform_client.save_checkpoint.assert_called_once()

    # Verify payload sanitization (password field redacted)
    pushed_asset = mock_platform_client.push_assets.call_args[0][0][0]
    assert pushed_asset.id == "event-001"
    assert "password" not in pushed_asset.raw


@pytest.mark.asyncio
async def test_incremental_sync_with_checkpoint(mock_platform_client):
    """Verifies incremental sync applies lookback_buffer_seconds to existing checkpoint timestamp."""
    last_sync = datetime(2026, 9, 24, 10, 0, 0, tzinfo=timezone.utc)
    mock_platform_client.get_checkpoint.return_value = Checkpoint(
        connector="splunk_test",
        last_sync_timestamp=last_sync
    )

    engine = HardenedSyncEngine(
        connector_id="splunk_test",
        platform_client=mock_platform_client,
        lookback_buffer_seconds=120
    )

    fetch_events_fn = AsyncMock(return_value=[])

    result = await engine.execute_incremental_sync(fetch_events_fn)

    assert result.status == "success"
    assert result.assets_discovered == 0

    # Verify fetch_events_fn was called with buffer adjusted start_time (10:00:00 minus 120s = 09:58:00)
    called_kwargs = fetch_events_fn.call_args.kwargs
    expected_start = (last_sync - timedelta(seconds=120)).isoformat()
    assert called_kwargs["start_time"] == expected_start


@pytest.mark.asyncio
async def test_event_deduplication(mock_platform_client):
    """Verifies duplicate events with the same ID are deduplicated prior to pushing."""
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
    assert result.assets_pushed == 2  # Unique events only


@pytest.mark.asyncio
async def test_fetch_failure_handling(mock_platform_client):
    """Verifies fetch exception returns failure status gracefully without crashing."""
    engine = HardenedSyncEngine(
        connector_id="splunk_test",
        platform_client=mock_platform_client
    )

    fetch_events_fn = AsyncMock(side_effect=Exception("API Connection Timeout"))

    result = await engine.execute_incremental_sync(fetch_events_fn)

    assert result.status == "failure"
    assert result.assets_pushed == 0
    assert "API Connection Timeout" in result.errors[0]
