"""End-to-end authorization checks; run with the dedicated test database configured."""
import json
from fastapi.testclient import TestClient
from app.main import app

ADMIN_KEY = "test-admin-key-" + ("a" * 40)
USER_KEY = "test-viewer-key-" + ("b" * 40)

def test_mock_source_endpoints_and_low_privilege_denial(monkeypatch):
    monkeypatch.setenv("AEV_DATA_SOURCE", "mock")
    monkeypatch.setenv("AEV_API_KEYS_JSON", json.dumps({
        ADMIN_KEY: {"user_id": "admin", "role": "admin"},
        USER_KEY: {"user_id": "viewer1", "role": "user"},
    }))
    client = TestClient(app)
    admin_headers = {"Authorization": f"Bearer {ADMIN_KEY}"}
    user_headers = {"Authorization": f"Bearer {USER_KEY}"}

    summary = client.get("/copilot/executive-summary", headers=admin_headers)
    assert summary.status_code == 200
    assert summary.json()["data_source"] == "mock"
    assert summary.json()["metrics"]["total_assets"] >= 4

    search = client.post("/copilot/asset-search", headers=admin_headers,
                         json={"query": "finance workstation", "limit": 5})
    assert search.status_code == 200
    assert search.json()["data_source"] == "mock"
    assert search.json()["total_results"] >= 1

    freshness = client.get("/copilot/freshness-metrics", headers=admin_headers)
    assert freshness.status_code == 200
    assert freshness.json()["data_source"] == "mock"
    assert freshness.json()["total_assets"] == 5

    exposure = client.get("/copilot/exposure-explain/101", headers=admin_headers)
    assert exposure.status_code == 200
    assert exposure.json()["exposures"]

    audit = client.get("/copilot/permission-audit", headers=admin_headers)
    assert audit.status_code == 200
    assert audit.json()["mock_audit_evidence"]["restricted_asset_count"] >= 1
    assert audit.json()["mock_audit_evidence"]["denied_events"]

    # The seeded restricted records must not be available to a low-privilege key.
    assert client.get("/copilot/executive-summary", headers=user_headers).status_code == 403
    assert client.get("/copilot/permission-audit", headers=user_headers).status_code == 403
    assert client.get("/copilot/integrations", headers=user_headers).status_code == 403
    assert client.post("/copilot/asset-search", headers=user_headers,
                       json={"query": "finance", "limit": 5}).status_code == 403
