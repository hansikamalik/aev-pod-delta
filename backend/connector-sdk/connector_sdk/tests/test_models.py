from datetime import datetime, timezone

from connector_sdk import SyncResult, SyncStatus


def test_sync_result_duration_seconds():
    result = SyncResult(
        connector="sample",
        status=SyncStatus.SUCCESS,
        started_at=datetime(2026, 9, 23, 5, 0, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 9, 23, 5, 0, 2, 500000, tzinfo=timezone.utc),
    )

    assert result.duration_seconds == 2.5
