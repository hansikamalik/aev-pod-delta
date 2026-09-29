import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from sync_engine.engine import HardenedSyncEngine
from sync_engine.models import Asset, Checkpoint
from sync_engine.orchestrator import ConnectorSyncConfig, SyncRegistry, sync_all_connectors


class FakePlatformClient:
    def __init__(self, checkpoint=None, fail_push=False):
        self.checkpoint = checkpoint
        self.fail_push = fail_push
        self.pushed = []

    def get_checkpoint(self, connector_id):
        return self.checkpoint

    def save_checkpoint(self, checkpoint):
        self.checkpoint = checkpoint

    def push_assets(self, assets):
        if self.fail_push:
            raise RuntimeError("push down")
        self.pushed.extend(assets)


@pytest.fixture(autouse=True)
def fake_normalizer(monkeypatch):
    def _fake(event, connector_id):
        if event.get("bad"):
            raise ValueError("bad event")
        return Asset(id=event["id"], source=connector_id, name=event["id"], discoveredAt=event["ts"])

    monkeypatch.setattr("sync_engine.engine.normalize_event_to_asset", _fake)


def fetch_returning(events):
    async def _fetch(start_time, end_time):
        return events
    return _fetch


def run(coro):
    return asyncio.run(coro)


def ev(id_, seconds_ago):
    return {"id": id_, "ts": datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)}


def test_first_sync_is_full_and_saves_checkpoint():
    client = FakePlatformClient()
    engine = HardenedSyncEngine("c1", client)
    result = run(engine.execute_incremental_sync(fetch_returning([ev("a", 30), ev("b", 20)])))
    assert result.status == "success"
    assert result.mode == "full"
    assert result.assets_pushed == 2
    assert client.checkpoint is not None


def test_second_sync_with_no_changes_pushes_nothing():
    client = FakePlatformClient()
    engine = HardenedSyncEngine("c1", client)
    events = [ev("a", 30), ev("b", 20)]
    run(engine.execute_incremental_sync(fetch_returning(events)))
    result = run(engine.execute_incremental_sync(fetch_returning(events)))
    assert result.mode == "incremental"
    assert result.assets_pushed == 0
    assert result.assets_skipped == 2
    assert len(client.pushed) == 2


def test_only_new_record_is_pushed():
    client = FakePlatformClient()
    engine = HardenedSyncEngine("c1", client)
    a, b = ev("a", 30), ev("b", 20)
    run(engine.execute_incremental_sync(fetch_returning([a, b])))
    result = run(engine.execute_incremental_sync(fetch_returning([a, b, ev("c", 5)])))
    assert result.assets_pushed == 1
    assert [x.id for x in client.pushed] == ["a", "b", "c"]


def test_failed_push_does_not_advance_checkpoint():
    client = FakePlatformClient(fail_push=True)
    engine = HardenedSyncEngine("c1", client)
    result = run(engine.execute_incremental_sync(fetch_returning([ev("a", 10)])))
    assert result.status == "partial_failure"
    assert client.checkpoint is None


def test_empty_run_does_not_move_checkpoint_backwards():
    ts = datetime.now(timezone.utc) - timedelta(minutes=5)
    client = FakePlatformClient(checkpoint=Checkpoint(connector="c1", last_sync_timestamp=ts))
    engine = HardenedSyncEngine("c1", client)
    run(engine.execute_incremental_sync(fetch_returning([])))
    assert client.checkpoint.last_sync_timestamp == ts


def test_future_checkpoint_falls_back_to_full():
    future = datetime.now(timezone.utc) + timedelta(days=2)
    client = FakePlatformClient(checkpoint=Checkpoint(connector="c1", last_sync_timestamp=future))
    engine = HardenedSyncEngine("c1", client)
    result = run(engine.execute_incremental_sync(fetch_returning([ev("a", 10)])))
    assert result.mode == "full"
    assert client.checkpoint.last_sync_timestamp <= datetime.now(timezone.utc)


def test_force_full_ignores_checkpoint():
    ts = datetime.now(timezone.utc) - timedelta(minutes=1)
    client = FakePlatformClient(checkpoint=Checkpoint(connector="c1", last_sync_timestamp=ts))
    seen = {}

    async def fetch(start_time, end_time):
        seen["start"] = datetime.fromisoformat(start_time)
        return []

    engine = HardenedSyncEngine("c1", client)
    result = run(engine.execute_incremental_sync(fetch, default_lookback_days=7, force_full=True))
    assert result.mode == "full"
    assert seen["start"] < datetime.now(timezone.utc) - timedelta(days=6)


def test_fetch_retries_then_succeeds():
    calls = {"n": 0}

    async def flaky(start_time, end_time):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("timeout")
        return [ev("a", 5)]

    engine = HardenedSyncEngine("c1", FakePlatformClient(), retry_base_delay_seconds=0)
    result = run(engine.execute_incremental_sync(flaky))
    assert result.status == "success"
    assert calls["n"] == 3


def test_fetch_failure_returns_failure_and_keeps_checkpoint():
    async def broken(start_time, end_time):
        raise RuntimeError("down")

    client = FakePlatformClient()
    engine = HardenedSyncEngine("c1", client, retry_base_delay_seconds=0)
    result = run(engine.execute_incremental_sync(broken))
    assert result.status == "failure"
    assert client.checkpoint is None


def test_bad_event_is_skipped_not_fatal():
    client = FakePlatformClient()
    engine = HardenedSyncEngine("c1", client)
    events = [ev("a", 10), {"id": "x", "ts": datetime.now(timezone.utc), "bad": True}]
    result = run(engine.execute_incremental_sync(fetch_returning(events)))
    assert result.assets_pushed == 1
    assert result.status == "partial_failure"
    assert len(result.errors) == 1


def test_naive_datetime_does_not_crash():
    client = FakePlatformClient()
    engine = HardenedSyncEngine("c1", client)
    naive = {"id": "n", "ts": datetime.utcnow()}
    result = run(engine.execute_incremental_sync(fetch_returning([naive])))
    assert result.assets_pushed == 1


def test_sync_all_isolates_failures():
    async def ok(start_time, end_time):
        return [ev("a", 5)]

    async def boom(start_time, end_time):
        raise RuntimeError("vendor down")

    registry = SyncRegistry()
    registry.register(ConnectorSyncConfig("good", ok))
    registry.register(ConnectorSyncConfig("bad", boom))

    results = run(sync_all_connectors(registry, FakePlatformClient()))
    assert results["good"].status == "success"
    assert results["bad"].status == "failure"
