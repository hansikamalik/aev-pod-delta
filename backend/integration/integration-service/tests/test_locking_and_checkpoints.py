"""
Unit tests for P1-2: Redis Distributed Locking & PostgreSQL-Backed Sync Checkpoints.
Verifies mutex lock acquisition, concurrent sync rejection (409 Conflict), and checkpoint tracking.
"""

from datetime import datetime, timezone
from fastapi.testclient import TestClient
import pytest

from app.locking import SyncLockManager, sync_lock_manager
from app.main import app
from app.models import SyncCheckpoint
from app.storage import storage


@pytest.fixture(autouse=True)
def clean_state():
    """Ensure clean storage and lock manager state between tests."""
    storage.clear()
    sync_lock_manager.clear()
    yield
    storage.clear()
    sync_lock_manager.clear()


@pytest.fixture
def client():
    return TestClient(app)


class TestSyncLockManager:
    """Test distributed lock acquisition, conflict detection, and release."""

    def test_acquire_and_release_lock(self):
        manager = SyncLockManager()
        # Acquire
        assert manager.acquire_lock("int-123", "job-aaa", ttl_seconds=60) is True
        assert manager.get_active_job("int-123") == "job-aaa"

        # Second acquisition on same integration fails
        assert manager.acquire_lock("int-123", "job-bbb", ttl_seconds=60) is False

        # Release from wrong job fails
        assert manager.release_lock("int-123", "job-wrong") is False
        assert manager.get_active_job("int-123") == "job-aaa"

        # Release from correct job succeeds
        assert manager.release_lock("int-123", "job-aaa") is True
        assert manager.get_active_job("int-123") is None

        # Now can acquire again
        assert manager.acquire_lock("int-123", "job-bbb", ttl_seconds=60) is True
        manager.release_lock("int-123", "job-bbb")

    def test_different_integrations_do_not_block_each_other(self):
        manager = SyncLockManager()
        assert manager.acquire_lock("int-aws", "job-1", ttl_seconds=60) is True
        assert manager.acquire_lock("int-gcp", "job-2", ttl_seconds=60) is True

        manager.release_lock("int-aws", "job-1")
        manager.release_lock("int-gcp", "job-2")


class TestConcurrentSyncAPIRoute:
    """Test REST API behavior under concurrent sync triggers."""

    def test_concurrent_sync_returns_409_conflict(self, client):
        # 1. Create an integration
        create_resp = client.post(
            "/api/v1/integrations",
            json={
                "name": "AWS Production Account",
                "connector_type": "aws",
                "config": {"region": "us-east-1"},
            },
        )
        assert create_resp.status_code == 201
        int_id = create_resp.json()["id"]

        # 2. Simulate another running sync worker holding the lock
        lock_held = sync_lock_manager.acquire_lock(int_id, "job-running-now", ttl_seconds=120)
        assert lock_held is True

        # 3. Trigger sync via API while lock is held
        sync_resp = client.post(f"/api/v1/integrations/{int_id}/sync")
        assert sync_resp.status_code == 409
        detail = sync_resp.json()["detail"]
        assert detail["error"] == "sync_in_progress"
        assert detail["job_id"] == "job-running-now"
        assert detail["integration_id"] == int_id

        # 4. Release lock, sync should now succeed
        sync_lock_manager.release_lock(int_id, "job-running-now")
        sync_resp_ok = client.post(f"/api/v1/integrations/{int_id}/sync")
        assert sync_resp_ok.status_code == 200
        assert sync_resp_ok.json()["status"] == "success"

    def test_sync_records_and_retrieves_checkpoint(self, client):
        # 1. Create an integration
        create_resp = client.post(
            "/api/v1/integrations",
            json={
                "name": "GCP Data Analytics",
                "connector_type": "gcp",
                "config": {"project_id": "aev-prod"},
            },
        )
        int_id = create_resp.json()["id"]

        # 2. Verify no checkpoint exists initially
        cp_init = client.get(f"/api/v1/integrations/{int_id}/checkpoint")
        assert cp_init.status_code == 404

        # 3. Run sync
        sync_resp = client.post(f"/api/v1/integrations/{int_id}/sync")
        assert sync_resp.status_code == 200

        # 4. Checkpoint now exists and contains cursor and metrics
        cp_resp = client.get(f"/api/v1/integrations/{int_id}/checkpoint")
        assert cp_resp.status_code == 200
        cp_data = cp_resp.json()
        assert cp_data["integration_id"] == int_id
        assert cp_data["status"] == "success"
        assert cp_data["assets_discovered"] == 7
        assert cp_data["last_cursor"] is not None
        assert "cursor-" in cp_data["last_cursor"]
