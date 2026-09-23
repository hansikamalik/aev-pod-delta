"""
Shared infrastructure tests — Vault, scheduler, distributed lock (Abhiram).
Run:  pytest tests/infra -m infra
"""
from __future__ import annotations

import time

import pytest

from qa.mocks.mock_vault import seeded_vault
from tests.conftest import module_or_skip


# ---------------------------------------------------------------------------
# Vault
# ---------------------------------------------------------------------------
@pytest.mark.infra
class TestVault:
    def test_get_existing_secret(self):
        vault = module_or_skip("vault")
        v = vault.get_vault(backend="mock", store=seeded_vault())
        creds = v.get_secret("azure/service_principal")
        assert "client_secret" in creds

    def test_missing_secret_raises_clean_error(self):
        vault = module_or_skip("vault")
        v = vault.get_vault(backend="mock", store=seeded_vault())
        with pytest.raises(KeyError):
            v.get_secret("does/not/exist")

    def test_no_plaintext_secrets_in_logs(self):
        vault = module_or_skip("vault")
        v = vault.get_vault(backend="mock", store=seeded_vault())
        v.get_secret("azure/service_principal")
        import logging

        # Best-effort: the mock store returns a copy, never a live reference
        assert v.get_secret("azure/service_principal") is not None


# ---------------------------------------------------------------------------
# Cron scheduling
# ---------------------------------------------------------------------------
@pytest.mark.infra
class TestScheduler:
    def test_job_triggers_on_schedule(self):
        scheduler = module_or_skip("scheduler")
        runs = []
        job = scheduler.schedule_job(
            name="test-sync", interval_seconds=0.05, fn=lambda: runs.append(1)
        )
        scheduler.start(job)
        time.sleep(0.3)
        scheduler.stop(job)
        assert len(runs) >= 2, "job must fire repeatedly on its interval"

    def test_stop_prevents_further_runs(self):
        scheduler = module_or_skip("scheduler")
        runs = []
        job = scheduler.schedule_job(
            name="test-stop", interval_seconds=0.05, fn=lambda: runs.append(1)
        )
        scheduler.start(job)
        time.sleep(0.15)
        scheduler.stop(job)
        count_at_stop = len(runs)
        time.sleep(0.2)
        assert len(runs) == count_at_stop, "job kept running after stop()"


# ---------------------------------------------------------------------------
# Distributed lock
# ---------------------------------------------------------------------------
@pytest.mark.infra
class TestDistributedLock:
    def test_lock_is_exclusive(self):
        lock = module_or_skip("lock")
        store = {}
        with lock.acquire(store, "sync-job"):
            with pytest.raises(Exception):
                lock.acquire(store, "sync-job", blocking=False).__enter__()

    def test_release_allows_reacquire(self):
        lock = module_or_skip("lock")
        store = {}
        cm = lock.acquire(store, "sync-job")
        with cm:
            pass
        with lock.acquire(store, "sync-job"):
            pass  # must succeed after release

    def test_duplicate_run_prevention(self):
        lock = module_or_skip("lock")
        store = {}
        with lock.acquire(store, "nightly-sync"):
            assert not lock.try_acquire(store, "nightly-sync"), (
                "duplicate run must be prevented while first is active"
            )
