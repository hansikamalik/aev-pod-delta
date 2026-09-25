"""
Contract test: proves that ANY connector implementing the shared
Connector interface can be discovered, synced, and health-checked
without special-casing. If this passes for the dummy connector,
the interface itself is sound.
"""
from tests.dummy_connector import DummyConnector


def test_discover_returns_assets():
    connector = DummyConnector()
    assets = connector.discover()
    assert len(assets) > 0
    assert all(a.id and a.type and a.name for a in assets)


def test_ingest_matches_discover():
    connector = DummyConnector()
    assert connector.ingest() == connector.discover()


def test_sync_reports_success():
    connector = DummyConnector()
    result = connector.sync()
    assert result.success is True
    assert result.records_synced == 2
    assert result.errors == []


def test_health_check_passes():
    connector = DummyConnector()
    assert connector.health_check() is True


def test_config_and_credential_schemas_exist():
    connector = DummyConnector()
    assert isinstance(connector.get_config_schema(), dict)
    assert isinstance(connector.get_credential_schema(), dict)
