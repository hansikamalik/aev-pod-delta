from connector_sdk import SampleConnector, SyncStatus


def test_discover_returns_assets():
    connector = SampleConnector()
    assets = list(connector.discover())
    assert len(assets) == 3
    assert all(a.source == "sample" for a in assets)


def test_ingest_pushes_all_assets():
    connector = SampleConnector()
    assets = list(connector.discover())
    pushed = connector.ingest(assets)
    assert pushed == len(assets)


def test_sync_success_path():
    connector = SampleConnector()
    result = connector.sync()
    assert result.status == SyncStatus.SUCCESS
    assert result.assets_discovered == 3
    assert result.assets_pushed == 3
    assert result.errors == []


def test_sync_failure_path():
    connector = SampleConnector(simulate_failure=True)
    result = connector.sync()
    assert result.status == SyncStatus.FAILED
    assert result.assets_pushed == 0
    assert len(result.errors) == 1


def test_check_health():
    assert SampleConnector().check_health() is True
    assert SampleConnector(simulate_failure=True).check_health() is False


def test_describe_config_and_credentials_are_schema_dicts():
    connector = SampleConnector()
    config_schema = connector.describe_config()
    cred_schema = connector.describe_credentials()
    assert config_schema["type"] == "object"
    assert "api_key" in cred_schema["properties"]
    assert "api_key" in cred_schema["required"]
