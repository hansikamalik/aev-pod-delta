import pytest
from connector_sdk import AssetType, SyncStatus

from crowdstrike_connector import CrowdStrikeConnector, FakeFalconClient


# ---- discovery & normalisation -----------------------------------------

def test_discover_returns_assets():
    connector = CrowdStrikeConnector(client=FakeFalconClient())
    assets = list(connector.discover())
    assert len(assets) > 0


def test_discover_hosts():
    connector = CrowdStrikeConnector(client=FakeFalconClient())
    assets = list(connector.discover())
    hosts = [a for a in assets if a.type == AssetType.COMPUTE]
    assert len(hosts) == 3
    assert all(a.source == "crowdstrike" for a in hosts)


def test_discover_detections():
    connector = CrowdStrikeConnector(client=FakeFalconClient())
    assets = list(connector.discover())
    detections = [a for a in assets if a.type == AssetType.DETECTION]
    assert len(detections) == 2
    assert all(a.source == "crowdstrike" for a in detections)


def test_host_asset_has_required_tags():
    connector = CrowdStrikeConnector(client=FakeFalconClient())
    assets = list(connector.discover())
    laptop = next(a for a in assets if a.name == "LAPTOP-FINTECH-001")
    assert laptop.tags["platform"] == "Windows"
    assert laptop.tags["os_version"] == "Windows 11"
    assert laptop.tags["status"] == "normal"
    assert laptop.tags["external_ip"] == "203.0.113.10"


def test_contained_host_status_tag():
    connector = CrowdStrikeConnector(client=FakeFalconClient())
    assets = list(connector.discover())
    contained = next(a for a in assets if a.name == "WORKSTATION-TRADER-05")
    assert contained.tags["status"] == "contained"


def test_detection_has_severity_tag():
    connector = CrowdStrikeConnector(client=FakeFalconClient())
    assets = list(connector.discover())
    detections = [a for a in assets if a.type == AssetType.DETECTION]
    severities = {a.tags["severity"] for a in detections}
    assert "High" in severities
    assert "Critical" in severities


def test_detection_has_tactic_and_technique():
    connector = CrowdStrikeConnector(client=FakeFalconClient())
    assets = list(connector.discover())
    detection = next(a for a in assets if a.tags.get("severity") == "Critical")
    assert detection.tags["tactic"] == "Impact"
    assert detection.tags["technique"] == "Data Encrypted for Impact"


def test_detection_name_truncated_to_120_chars():
    connector = CrowdStrikeConnector(client=FakeFalconClient())
    assets = list(connector.discover())
    for a in assets:
        if a.type == AssetType.DETECTION:
            assert len(a.name) <= 120


# ---- ingest ------------------------------------------------------------

def test_ingest_returns_count():
    connector = CrowdStrikeConnector(client=FakeFalconClient())
    assets = list(connector.discover())
    pushed = connector.ingest(assets)
    assert pushed == len(assets)


# ---- sync --------------------------------------------------------------

def test_sync_success():
    connector = CrowdStrikeConnector(client=FakeFalconClient())
    result = connector.sync()
    assert result.status == SyncStatus.SUCCESS
    assert result.assets_discovered > 0
    assert result.assets_pushed == result.assets_discovered
    assert result.errors == []


def test_sync_failure_on_discover_error():
    connector = CrowdStrikeConnector(client=FakeFalconClient())

    def bad_discover():
        raise ConnectionError("simulated Falcon API failure")

    connector.discover = bad_discover  # type: ignore
    result = connector.sync()
    assert result.status == SyncStatus.FAILED
    assert result.assets_pushed == 0
    assert len(result.errors) == 1


# ---- health check -------------------------------------------------------

def test_check_health_true():
    connector = CrowdStrikeConnector(client=FakeFalconClient())
    assert connector.check_health() is True


def test_check_health_false():
    connector = CrowdStrikeConnector(client=FakeFalconClient(fail_ping=True))
    assert connector.check_health() is False


# ---- schema methods -----------------------------------------------------

def test_describe_config_has_base_url():
    connector = CrowdStrikeConnector(client=FakeFalconClient())
    schema = connector.describe_config()
    assert schema["type"] == "object"
    assert "base_url" in schema["properties"]


def test_describe_credentials_has_client_id_and_secret():
    connector = CrowdStrikeConnector(client=FakeFalconClient())
    schema = connector.describe_credentials()
    assert "client_id" in schema["properties"]
    assert "client_secret" in schema["properties"]
    assert schema["properties"]["client_id"]["secret"] is True
    assert schema["properties"]["client_secret"]["secret"] is True
    assert "client_id" in schema["required"]
    assert "client_secret" in schema["required"]
