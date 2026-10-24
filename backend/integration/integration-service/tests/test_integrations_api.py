"""
Comprehensive test suite for the Integration Service Management REST API.
Validates all CRUD, health check, synchronization, and history endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.storage import storage


@pytest.fixture(autouse=True)
def clean_storage():
    """Clear repository before each test."""
    storage.clear()
    yield
    storage.clear()


@pytest.fixture
def client():
    return TestClient(app)


# ---- 1. Catalog Tests -------------------------------------------------------

def test_get_catalog_returns_supported_connectors(client):
    res = client.get("/api/v1/integrations/catalog")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 5
    types = [item["connector_type"] for item in data]
    assert "aws" in types
    assert "gcp" in types
    assert "crowdstrike" in types
    assert "jira" in types
    assert "sample" in types

    aws_item = next(item for item in data if item["connector_type"] == "aws")
    assert "region" in aws_item["config_schema"]["properties"]
    assert "access_key_id" in aws_item["credential_schema"]["properties"]


# ---- 2. CRUD Tests ----------------------------------------------------------

def test_create_integration_success(client):
    payload = {
        "name": "Production AWS Account",
        "connector_type": "aws",
        "config": {"region": "us-east-1"},
        "credentials": {"access_key_id": "AKIA_FAKE", "secret_access_key": "SECRET_FAKE"},
        "schedule": "every 30m",
        "enabled": True,
    }
    res = client.post("/api/v1/integrations", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["id"].startswith("int-")
    assert data["name"] == "Production AWS Account"
    assert data["connector_type"] == "aws"
    assert data["credentials_configured"] is True
    # Secrets must NEVER be leaked in responses
    assert "access_key_id" not in data
    assert "credentials" not in data


def test_create_integration_rejects_unknown_type(client):
    payload = {
        "name": "Invalid Connector",
        "connector_type": "unknown_vendor_xyz",
    }
    res = client.post("/api/v1/integrations", json=payload)
    assert res.status_code == 400
    assert "Unsupported connector type" in res.json()["detail"]


def test_list_integrations_with_filtering(client):
    client.post("/api/v1/integrations", json={"name": "AWS-1", "connector_type": "aws"})
    client.post("/api/v1/integrations", json={"name": "Jira-1", "connector_type": "jira"})

    res = client.get("/api/v1/integrations")
    assert res.status_code == 200
    assert len(res.json()) == 2

    res_aws = client.get("/api/v1/integrations?connector_type=aws")
    assert len(res_aws.json()) == 1
    assert res_aws.json()[0]["name"] == "AWS-1"


def test_get_integration_by_id(client):
    create_res = client.post("/api/v1/integrations", json={"name": "AWS-1", "connector_type": "aws"})
    int_id = create_res.json()["id"]

    res = client.get(f"/api/v1/integrations/{int_id}")
    assert res.status_code == 200
    assert res.json()["id"] == int_id


def test_get_nonexistent_integration_returns_404(client):
    res = client.get("/api/v1/integrations/int-fake999")
    assert res.status_code == 404


def test_update_integration(client):
    create_res = client.post("/api/v1/integrations", json={"name": "Old Name", "connector_type": "aws"})
    int_id = create_res.json()["id"]

    update_payload = {"name": "New Name", "schedule": "every 6h"}
    res = client.put(f"/api/v1/integrations/{int_id}", json=update_payload)
    assert res.status_code == 200
    assert res.json()["name"] == "New Name"
    assert res.json()["schedule"] == "every 6h"


def test_delete_integration(client):
    create_res = client.post("/api/v1/integrations", json={"name": "To Delete", "connector_type": "sample"})
    int_id = create_res.json()["id"]

    del_res = client.delete(f"/api/v1/integrations/{int_id}")
    assert del_res.status_code == 204

    get_res = client.get(f"/api/v1/integrations/{int_id}")
    assert get_res.status_code == 404


# ---- 3. Operational Tests (Health Check & Sync) -----------------------------

def test_health_check_endpoint(client):
    create_res = client.post("/api/v1/integrations", json={"name": "Live AWS", "connector_type": "aws"})
    int_id = create_res.json()["id"]

    test_res = client.post(f"/api/v1/integrations/{int_id}/test")
    assert test_res.status_code == 200
    data = test_res.json()
    assert data["healthy"] is True
    assert data["status"] == "healthy"

    # Status should reflect in GET /integrations/{id}
    get_res = client.get(f"/api/v1/integrations/{int_id}")
    assert get_res.json()["health_status"] == "healthy"


def test_trigger_sync_endpoint(client):
    create_res = client.post("/api/v1/integrations", json={"name": "CrowdStrike Prod", "connector_type": "crowdstrike"})
    int_id = create_res.json()["id"]

    sync_res = client.post(f"/api/v1/integrations/{int_id}/sync")
    assert sync_res.status_code == 200
    job = sync_res.json()
    assert job["job_id"].startswith("job-")
    assert job["status"] == "success"
    assert job["assets_discovered"] == 5
    assert job["assets_pushed"] == 5
    assert job["duration_seconds"] >= 0

    # Status updated on parent integration
    get_res = client.get(f"/api/v1/integrations/{int_id}")
    assert get_res.json()["last_sync_status"] == "SUCCESS"
    assert get_res.json()["last_assets_discovered"] == 5


def test_disable_and_enable_integration(client):
    create_res = client.post("/api/v1/integrations", json={"name": "GCP Sync", "connector_type": "gcp"})
    int_id = create_res.json()["id"]

    # Disable
    dis_res = client.patch(f"/api/v1/integrations/{int_id}/disable")
    assert dis_res.status_code == 200
    assert dis_res.json()["enabled"] is False

    # Sync attempt should fail when disabled
    sync_res = client.post(f"/api/v1/integrations/{int_id}/sync")
    assert sync_res.status_code == 400
    assert "disabled" in sync_res.json()["detail"]

    # Re-enable
    en_res = client.patch(f"/api/v1/integrations/{int_id}/enable")
    assert en_res.status_code == 200
    assert en_res.json()["enabled"] is True

    # Sync now succeeds
    sync_res2 = client.post(f"/api/v1/integrations/{int_id}/sync")
    assert sync_res2.status_code == 200
    assert sync_res2.json()["status"] == "success"


def test_get_sync_history(client):
    create_res = client.post("/api/v1/integrations", json={"name": "Jira Sync", "connector_type": "jira"})
    int_id = create_res.json()["id"]

    # Run 2 syncs
    client.post(f"/api/v1/integrations/{int_id}/sync")
    client.post(f"/api/v1/integrations/{int_id}/sync")

    hist_res = client.get(f"/api/v1/integrations/{int_id}/history")
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) == 2
    assert all(j["integration_id"] == int_id for j in history)


def test_list_all_platform_jobs(client):
    aws = client.post("/api/v1/integrations", json={"name": "AWS", "connector_type": "aws"}).json()
    gcp = client.post("/api/v1/integrations", json={"name": "GCP", "connector_type": "gcp"}).json()

    client.post(f"/api/v1/integrations/{aws['id']}/sync")
    client.post(f"/api/v1/integrations/{gcp['id']}/sync")

    jobs_res = client.get("/api/v1/integrations/jobs/all")
    assert jobs_res.status_code == 200
    assert len(jobs_res.json()) == 2
