import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from secrets_vault import (
    MockVaultBackend,
    SecretNotFoundError,
    SecretsVaultClient,
    VaultUnavailableError,
)
from distributed_lock import DistributedLock, LockAcquisitionError, MockLockBackend
from scheduler import CronScheduler
from dummy_connector import DummyConnector


# -- Secrets Vault ------------------------------------------------------------

def test_get_credential_success():
    backend = MockVaultBackend(seed_secrets={"azure/sp": "secret-value"})
    vault = SecretsVaultClient(backend)
    assert vault.get_credential("azure/sp") == "secret-value"


def test_get_credential_not_found():
    backend = MockVaultBackend()
    vault = SecretsVaultClient(backend)
    with pytest.raises(SecretNotFoundError):
        vault.get_credential("missing/key")


def test_get_credential_retries_then_succeeds():
    backend = MockVaultBackend(seed_secrets={"k": "v"}, unavailable_for_n_calls=2)
    vault = SecretsVaultClient(backend, max_retries=3, backoff_base_seconds=0.001)
    assert vault.get_credential("k") == "v"


def test_get_credential_gives_up_after_max_retries():
    backend = MockVaultBackend(seed_secrets={"k": "v"}, unavailable_for_n_calls=10)
    vault = SecretsVaultClient(backend, max_retries=2, backoff_base_seconds=0.001)
    with pytest.raises(VaultUnavailableError):
        vault.get_credential("k")


def test_credential_caching():
    backend = MockVaultBackend(seed_secrets={"k": "v1"})
    vault = SecretsVaultClient(backend)
    assert vault.get_credential("k") == "v1"
    backend.put("k", "v2")
    assert vault.get_credential("k") == "v1"  # cached
    vault.invalidate_cache("k")
    assert vault.get_credential("k") == "v2"


# -- Distributed Lock ---------------------------------------------------------

def test_lock_acquire_and_release():
    lock = DistributedLock(MockLockBackend(), default_ttl_seconds=5)
    with lock.acquire("job:test") as token:
        assert token
        assert lock.is_locked("job:test")
    assert not lock.is_locked("job:test")


def test_lock_prevents_concurrent_acquisition():
    backend = MockLockBackend()
    lock = DistributedLock(backend, default_ttl_seconds=30)
    token1 = lock.acquire_raw("job:x")
    with pytest.raises(LockAcquisitionError):
        lock.acquire_raw("job:x")
    lock.release_raw("job:x", token1)
    token2 = lock.acquire_raw("job:x")  # succeeds after release
    assert token2 != token1


def test_lock_expires_after_ttl():
    backend = MockLockBackend()
    lock = DistributedLock(backend, default_ttl_seconds=0.01)
    lock.acquire_raw("job:y")
    import time
    time.sleep(0.02)
    # Expired, so a new acquire should succeed without needing release.
    token2 = lock.acquire_raw("job:y")
    assert token2


# -- Scheduler ----------------------------------------------------------------

def test_scheduler_runs_due_jobs():
    lock = DistributedLock(MockLockBackend())
    scheduler = CronScheduler(lock)
    connector = DummyConnector()
    connector.configure("dummy-cred")

    scheduler.register_job("dummy_sync", interval_seconds=10, fn=lambda: connector.sync({"n": 1}))

    ran = scheduler.tick(now=0)
    assert ran == ["dummy_sync"]
    assert connector.sync_count == 1

    # Not due yet
    ran_again = scheduler.tick(now=5)
    assert ran_again == []
    assert connector.sync_count == 1

    # Due again after interval elapses
    ran_later = scheduler.tick(now=11)
    assert ran_later == ["dummy_sync"]
    assert connector.sync_count == 2


def test_scheduler_prevents_duplicate_concurrent_run():
    backend = MockLockBackend()
    # Use a fake logical clock (list as mutable box) so the lock's notion of
    # "now" lines up with the fake scheduling clock passed to tick() below.
    fake_now = [0.0]
    lock = DistributedLock(backend, default_ttl_seconds=100, clock=lambda: fake_now[0])
    scheduler = CronScheduler(lock)
    scheduler.register_job("job1", interval_seconds=1, fn=lambda: None)

    # Simulate another worker already holding the lock for this job.
    backend.try_acquire("job:job1", owner_token="other-worker", ttl_seconds=100, now=fake_now[0])

    ran = scheduler.tick(now=0)
    assert ran == []
    assert scheduler.status()["job1"]["skipped_duplicate_runs"] == 1


def test_scheduler_rejects_duplicate_job_names():
    lock = DistributedLock(MockLockBackend())
    scheduler = CronScheduler(lock)
    scheduler.register_job("dup", interval_seconds=1, fn=lambda: None)
    with pytest.raises(ValueError):
        scheduler.register_job("dup", interval_seconds=1, fn=lambda: None)
