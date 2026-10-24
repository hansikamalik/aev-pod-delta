import pytest
from connector_sdk import AssetType, SyncStatus

from gcp_connector import FakeGCPClient, GCPConnector


# ---- discovery & normalisation -----------------------------------------

def test_discover_returns_assets():
    connector = GCPConnector(project_id="my-project-123", client=FakeGCPClient())
    assets = list(connector.discover())
    assert len(assets) > 0


def test_discover_compute_instances():
    connector = GCPConnector(project_id="my-project-123", client=FakeGCPClient())
    assets = list(connector.discover())
    compute = [a for a in assets if a.type == AssetType.COMPUTE]
    assert len(compute) == 2
    assert all(a.source == "gcp" for a in compute)


def test_discover_storage_buckets():
    connector = GCPConnector(project_id="my-project-123", client=FakeGCPClient())
    assets = list(connector.discover())
    buckets = [a for a in assets if a.type == AssetType.STORAGE and "gcs" in a.name]
    assert len(buckets) == 2


def test_discover_service_accounts():
    connector = GCPConnector(project_id="my-project-123", client=FakeGCPClient())
    assets = list(connector.discover())
    identities = [a for a in assets if a.type == AssetType.IDENTITY]
    assert len(identities) == 2
    names = [a.name for a in identities]
    assert "AEV Backend Service Account" in names


def test_compute_instance_has_zone_tag():
    connector = GCPConnector(project_id="my-project-123", client=FakeGCPClient())
    assets = list(connector.discover())
    instance = next(a for a in assets if a.name == "api-server-prod-1")
    assert instance.tags["zone"] == "us-central1-a"
    assert instance.tags["status"] == "RUNNING"
    assert instance.tags["machine_type"] == "n2-standard-4"


def test_bucket_has_location_tag():
    connector = GCPConnector(project_id="my-project-123", client=FakeGCPClient())
    assets = list(connector.discover())
    bucket = next(a for a in assets if a.name == "aev-gcs-uploads-prod")
    assert bucket.tags["location"] == "US"
    assert bucket.tags["storage_class"] == "STANDARD"


def test_disabled_service_account_tag():
    connector = GCPConnector(project_id="my-project-123", client=FakeGCPClient())
    assets = list(connector.discover())
    legacy = next(a for a in assets if "legacy" in a.name.lower())
    assert legacy.tags["disabled"] == "True"


def test_sql_instance_discovered():
    connector = GCPConnector(project_id="my-project-123", client=FakeGCPClient())
    assets = list(connector.discover())
    sql = [a for a in assets if a.type == AssetType.STORAGE and "postgres" in a.name]
    assert len(sql) == 1
    assert sql[0].tags["database_version"] == "POSTGRES_15"


# ---- ingest ------------------------------------------------------------

def test_ingest_returns_count():
    connector = GCPConnector(project_id="my-project-123", client=FakeGCPClient())
    assets = list(connector.discover())
    pushed = connector.ingest(assets)
    assert pushed == len(assets)


# ---- sync --------------------------------------------------------------

def test_sync_success():
    connector = GCPConnector(project_id="my-project-123", client=FakeGCPClient())
    result = connector.sync()
    assert result.status == SyncStatus.SUCCESS
    assert result.assets_discovered > 0
    assert result.assets_pushed == result.assets_discovered
    assert result.errors == []


def test_sync_failure_on_discover_error():
    connector = GCPConnector(project_id="my-project-123", client=FakeGCPClient())

    def bad_discover():
        raise ConnectionError("simulated GCP API failure")

    connector.discover = bad_discover  # type: ignore
    result = connector.sync()
    assert result.status == SyncStatus.FAILED
    assert result.assets_pushed == 0
    assert len(result.errors) == 1


# ---- health check -------------------------------------------------------

def test_check_health_true():
    connector = GCPConnector(project_id="my-project-123", client=FakeGCPClient())
    assert connector.check_health() is True


def test_check_health_false():
    connector = GCPConnector(project_id="my-project-123", client=FakeGCPClient(fail_ping=True))
    assert connector.check_health() is False


# ---- schema methods -----------------------------------------------------

def test_describe_config_has_project_id():
    connector = GCPConnector(project_id="my-project-123", client=FakeGCPClient())
    schema = connector.describe_config()
    assert schema["type"] == "object"
    assert "project_id" in schema["properties"]
    assert "project_id" in schema["required"]


def test_describe_credentials_has_credentials_json():
    connector = GCPConnector(project_id="my-project-123", client=FakeGCPClient())
    schema = connector.describe_credentials()
    assert "credentials_json" in schema["properties"]
    assert schema["properties"]["credentials_json"]["secret"] is True
    assert "credentials_json" in schema["required"]
