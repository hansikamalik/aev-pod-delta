import json

import pytest
from connector_sdk import AssetType, SyncStatus

from gcp_connector import FakeGCPAPIClient, GCPConnector, InMemoryPlatformClient
from gcp_connector.auth import GCPAuthError, GCPServiceAccountAuth

FAKE_KEY = json.dumps(
    {
        "type": "service_account",
        "project_id": "demo-project",
        "private_key": "-----BEGIN PRIVATE KEY-----\nFAKE\n-----END PRIVATE KEY-----\n",
        "client_email": "copilot-runner@demo-project.iam.gserviceaccount.com",
    }
)


# ---- discovery / normalization ---------------------------------------


def test_discover_returns_all_resource_types():
    connector = GCPConnector(project_id="demo-project", client=FakeGCPAPIClient())
    assets = list(connector.discover())

    # 2 instances + 1 bucket + 1 service account + 1 sql instance
    assert len(assets) == 5
    assert all(a.source == "gcp" for a in assets)

    types = {a.type for a in assets}
    assert types == {AssetType.COMPUTE, AssetType.STORAGE, AssetType.IDENTITY, AssetType.OTHER}


def test_compute_instances_normalized_with_zone_tag():
    connector = GCPConnector(project_id="demo-project", client=FakeGCPAPIClient())
    assets = [a for a in connector.discover() if a.type == AssetType.COMPUTE]

    assert len(assets) == 2
    assert assets[0].name == "app-server-1"
    assert assets[0].tags["zone"] == "us-central1-a"


def test_cloud_sql_normalized_as_other_with_resource_kind_tag():
    connector = GCPConnector(project_id="demo-project", client=FakeGCPAPIClient())
    sql_assets = [a for a in connector.discover() if a.tags.get("resource_kind") == "cloudsql"]

    assert len(sql_assets) == 1
    assert sql_assets[0].type == AssetType.OTHER
    assert sql_assets[0].name == "prod-postgres"


# ---- ingest / sync -----------------------------------------------------


def test_ingest_pushes_all_discovered_assets():
    platform = InMemoryPlatformClient()
    connector = GCPConnector(project_id="demo-project", client=FakeGCPAPIClient(), platform_client=platform)

    assets = list(connector.discover())
    pushed = connector.ingest(assets)

    assert pushed == len(assets) == 5
    assert platform.pushed == assets


def test_sync_success_path():
    connector = GCPConnector(project_id="demo-project", client=FakeGCPAPIClient())
    result = connector.sync()

    assert result.status == SyncStatus.SUCCESS
    assert result.assets_discovered == 5
    assert result.assets_pushed == 5
    assert result.errors == []


def test_sync_reports_failure_when_push_fails():
    connector = GCPConnector(
        project_id="demo-project",
        client=FakeGCPAPIClient(),
        platform_client=InMemoryPlatformClient(fail=True),
    )
    result = connector.sync()

    assert result.status == SyncStatus.FAILED
    assert result.assets_discovered == 5
    assert result.assets_pushed == 0
    assert len(result.errors) == 1


# ---- health check --------------------------------------------------


def test_check_health_true_and_false():
    healthy = GCPConnector(project_id="demo-project", client=FakeGCPAPIClient())
    unhealthy = GCPConnector(project_id="demo-project", client=FakeGCPAPIClient(fail_ping=True))

    assert healthy.check_health() is True
    assert unhealthy.check_health() is False


def test_check_health_false_when_no_credentials_configured():
    # No client and no service_account_key_json supplied -> can't auth.
    connector = GCPConnector(project_id="demo-project")
    assert connector.check_health() is False


# ---- config / credential schemas ---------------------------------------


def test_describe_config_and_credentials_are_schema_dicts():
    connector = GCPConnector(project_id="demo-project", client=FakeGCPAPIClient())

    config_schema = connector.describe_config()
    cred_schema = connector.describe_credentials()

    assert config_schema["type"] == "object"
    assert "project_id" in config_schema["properties"]

    assert "service_account_key_json" in cred_schema["properties"]
    assert cred_schema["properties"]["service_account_key_json"]["secret"] is True
    assert "service_account_key_json" in cred_schema["required"]


# ---- auth module ------------------------------------------------------


def test_auth_validate_matches_project_id():
    auth = GCPServiceAccountAuth(project_id="demo-project", service_account_key_json=FAKE_KEY)
    assert auth.validate() is True


def test_auth_rejects_mismatched_project():
    auth = GCPServiceAccountAuth(project_id="other-project", service_account_key_json=FAKE_KEY)
    assert auth.validate() is False


def test_auth_rejects_malformed_json():
    auth = GCPServiceAccountAuth(project_id="demo-project", service_account_key_json="not json")
    with pytest.raises(GCPAuthError):
        auth.validate()


def test_auth_rejects_missing_fields():
    bad_key = json.dumps({"type": "service_account", "project_id": "demo-project"})
    auth = GCPServiceAccountAuth(project_id="demo-project", service_account_key_json=bad_key)
    with pytest.raises(GCPAuthError):
        auth.validate()
