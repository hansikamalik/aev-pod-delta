import pytest
from connector_sdk import AssetType, SyncStatus

from aws_connector import AWSConnector, FakeAWSClient


# ---- discovery & normalisation -----------------------------------------

def test_discover_returns_assets():
    connector = AWSConnector(client=FakeAWSClient())
    assets = list(connector.discover())
    assert len(assets) > 0


def test_discover_ec2_instances():
    connector = AWSConnector(client=FakeAWSClient())
    assets = list(connector.discover())
    ec2_assets = [a for a in assets if a.type == AssetType.COMPUTE and a.tags.get("instance_type")]
    assert len(ec2_assets) == 2
    assert all(a.source == "aws" for a in ec2_assets)


def test_discover_s3_buckets():
    connector = AWSConnector(client=FakeAWSClient())
    assets = list(connector.discover())
    s3_assets = [a for a in assets if a.type == AssetType.STORAGE and "aev-" in a.name]
    assert len(s3_assets) >= 1


def test_discover_iam_roles():
    connector = AWSConnector(client=FakeAWSClient())
    assets = list(connector.discover())
    iam_assets = [a for a in assets if a.type == AssetType.IDENTITY]
    assert len(iam_assets) == 2
    role_names = [a.name for a in iam_assets]
    assert "legacy-admin" in role_names


def test_ec2_asset_has_required_tags():
    connector = AWSConnector(client=FakeAWSClient())
    assets = list(connector.discover())
    ec2 = next(a for a in assets if a.id == "i-0abc123456")
    assert ec2.name == "web-server-prod"
    assert ec2.tags["state"] == "running"
    assert ec2.tags["instance_type"] == "t3.medium"


def test_s3_asset_public_access_tag():
    connector = AWSConnector(client=FakeAWSClient())
    assets = list(connector.discover())
    bucket = next(a for a in assets if a.name == "aev-app-uploads-prod")
    # FakeAWSClient sets BlockPublicAcls=False → public_access="False"
    assert bucket.tags["public_access"] == "False"


def test_iam_role_has_arn_tag():
    connector = AWSConnector(client=FakeAWSClient())
    assets = list(connector.discover())
    role = next(a for a in assets if a.name == "ec2-ssm-role")
    assert "arn:aws:iam" in role.tags["arn"]


# ---- ingest ------------------------------------------------------------

def test_ingest_returns_count():
    connector = AWSConnector(client=FakeAWSClient())
    assets = list(connector.discover())
    pushed = connector.ingest(assets)
    assert pushed == len(assets)


# ---- sync --------------------------------------------------------------

def test_sync_success():
    connector = AWSConnector(client=FakeAWSClient())
    result = connector.sync()
    assert result.status == SyncStatus.SUCCESS
    assert result.assets_discovered > 0
    assert result.assets_pushed == result.assets_discovered
    assert result.errors == []


def test_sync_failure_on_discover_error():
    connector = AWSConnector(client=FakeAWSClient(fail_ping=True))
    # Simulate discover raising an exception by patching
    original_discover = connector.discover

    def bad_discover():
        raise ConnectionError("simulated AWS API failure")

    connector.discover = bad_discover  # type: ignore
    result = connector.sync()
    assert result.status == SyncStatus.FAILED
    assert result.assets_pushed == 0
    assert len(result.errors) == 1


# ---- health check -------------------------------------------------------

def test_check_health_true():
    connector = AWSConnector(client=FakeAWSClient())
    assert connector.check_health() is True


def test_check_health_false():
    connector = AWSConnector(client=FakeAWSClient(fail_ping=True))
    assert connector.check_health() is False


# ---- schema methods -----------------------------------------------------

def test_describe_config_has_region():
    connector = AWSConnector(client=FakeAWSClient())
    schema = connector.describe_config()
    assert schema["type"] == "object"
    assert "region" in schema["properties"]
    assert "region" in schema["required"]


def test_describe_credentials_has_keys():
    connector = AWSConnector(client=FakeAWSClient())
    schema = connector.describe_credentials()
    assert "access_key_id" in schema["properties"]
    assert "secret_access_key" in schema["properties"]
    assert schema["properties"]["access_key_id"]["secret"] is True
    assert schema["properties"]["secret_access_key"]["secret"] is True
    assert "access_key_id" in schema["required"]
    assert "secret_access_key" in schema["required"]
