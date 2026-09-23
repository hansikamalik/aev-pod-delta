import random
from datetime import UTC, datetime, timedelta

import pytest

from aev_connectors.webhook.config import RetryPolicy
from aev_connectors.webhook.delivery_log import InMemoryDeliveryLog
from aev_connectors.webhook.models import DeliveryRecord, DeliveryStatus, Subscription
from aev_connectors.webhook.retry import backoff_delay, next_retry_at, should_retry
from aev_connectors.webhook.subscriptions import InMemorySubscriptionStore, SubscriptionError


def _sub(**overrides) -> Subscription:
    base = dict(
        org_id="org_1",
        connector_id="webhook-custom-1",
        target_url="https://example.test/hook",
        event_types=["asset.created"],
    )
    base.update(overrides)
    return Subscription(**base)


# --------------------------------------------------------------- subscriptions

def test_create_and_get():
    store = InMemorySubscriptionStore()
    sub = store.create(_sub())
    assert store.get(sub.id).id == sub.id


def test_unknown_subscription_raises():
    store = InMemorySubscriptionStore()
    with pytest.raises(SubscriptionError, match="unknown"):
        store.get("sub_missing")


def test_unsupported_event_type_rejected():
    store = InMemorySubscriptionStore()
    with pytest.raises(SubscriptionError, match="unsupported"):
        store.create(_sub(event_types=["asset.exploded"]))


def test_empty_event_types_rejected():
    with pytest.raises(ValueError):
        _sub(event_types=[])


def test_event_types_deduplicated_and_sorted():
    sub = _sub(event_types=["asset.updated", "asset.created", "asset.created"])
    assert sub.event_types == ["asset.created", "asset.updated"]


@pytest.mark.parametrize(
    "patterns,event,expected",
    [
        (["asset.created"], "asset.created", True),
        (["asset.created"], "asset.updated", False),
        (["asset.*"], "asset.deleted", True),
        (["asset.*"], "exposure.created", False),
        (["*"], "scan.completed", True),
    ],
)
def test_matching_patterns(patterns, event, expected):
    assert _sub(event_types=patterns).matches(event) is expected


def test_inactive_subscription_never_matches():
    assert _sub(active=False).matches("asset.created") is False


def test_matching_scoped_to_org():
    store = InMemorySubscriptionStore()
    store.create(_sub(org_id="org_1"))
    store.create(_sub(org_id="org_2"))
    assert len(store.matching("org_1", "asset.created")) == 1


def test_update_and_delete():
    store = InMemorySubscriptionStore()
    sub = store.create(_sub())
    updated = store.update(sub.id, active=False)
    assert updated.active is False
    assert updated.updated_at >= sub.updated_at
    store.delete(sub.id)
    with pytest.raises(SubscriptionError):
        store.get(sub.id)


# ---------------------------------------------------------------------- retry

POLICY = RetryPolicy(max_attempts=4, base_delay_seconds=1.0, multiplier=2.0, jitter=False)


@pytest.mark.parametrize("attempt,expected", [(1, 1.0), (2, 2.0), (3, 4.0), (4, 8.0)])
def test_backoff_is_exponential(attempt, expected):
    assert backoff_delay(POLICY, attempt) == expected


def test_backoff_capped():
    policy = RetryPolicy(base_delay_seconds=1.0, max_delay_seconds=5.0, jitter=False)
    assert backoff_delay(policy, 10) == 5.0


def test_jitter_stays_within_bounds():
    policy = RetryPolicy(base_delay_seconds=2.0, jitter=True)
    rng = random.Random(42)
    for _ in range(50):
        assert 0.0 <= backoff_delay(policy, 3, rng) <= 8.0


@pytest.mark.parametrize("code", [429, 500, 502, 503, 504, 408])
def test_retryable_status_codes(code):
    assert should_retry(POLICY, 1, code, None) is True


@pytest.mark.parametrize("code", [200, 201, 400, 401, 403, 404, 422])
def test_non_retryable_status_codes(code):
    assert should_retry(POLICY, 1, code, None) is False


def test_transport_error_is_retryable():
    assert should_retry(POLICY, 1, None, "ConnectTimeout") is True


def test_stops_at_max_attempts():
    assert should_retry(POLICY, 4, 503, None) is False


def test_next_retry_at_moves_forward():
    now = datetime(2026, 9, 18, tzinfo=UTC)
    assert next_retry_at(POLICY, 2, now=now) == now + timedelta(seconds=2)


# --------------------------------------------------------------- delivery log

def _record(**overrides) -> DeliveryRecord:
    base = dict(
        org_id="org_1",
        connector_id="webhook-custom-1",
        subscription_id="sub_1",
        event_id="evt_1",
        event_type="asset.created",
        target_url="https://example.test/hook",
    )
    base.update(overrides)
    return DeliveryRecord(**base)


def test_log_lists_newest_first_and_filters_by_status():
    log = InMemoryDeliveryLog()
    log.append(_record(status=DeliveryStatus.DELIVERED))
    log.append(_record(status=DeliveryStatus.FAILED))
    assert len(log.list("org_1")) == 2
    assert len(log.list("org_1", DeliveryStatus.FAILED)) == 1
    assert log.list("org_2") == []


def test_due_for_retry_respects_next_retry_at():
    log = InMemoryDeliveryLog()
    now = datetime.now(UTC)
    log.append(
        _record(status=DeliveryStatus.RETRYING, next_retry_at=now - timedelta(seconds=1))
    )
    log.append(
        _record(status=DeliveryStatus.RETRYING, next_retry_at=now + timedelta(minutes=5))
    )
    assert len(log.due_for_retry(now)) == 1


def test_purge_expired_respects_retention():
    log = InMemoryDeliveryLog(retention_days=365)
    old = datetime.now(UTC) - timedelta(days=400)
    log.append(_record(created_at=old))
    log.append(_record())
    assert log.purge_expired() == 1
    assert len(log.list("org_1")) == 1


def test_stats_counts_every_status():
    log = InMemoryDeliveryLog()
    log.append(_record(status=DeliveryStatus.DELIVERED))
    log.append(_record(status=DeliveryStatus.DEAD_LETTERED))
    stats = log.stats("org_1")
    assert stats["delivered"] == 1
    assert stats["dead_lettered"] == 1
    assert stats["pending"] == 0
