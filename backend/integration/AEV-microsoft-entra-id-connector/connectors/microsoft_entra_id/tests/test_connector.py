"""End-to-end test of the EntraIDConnector pipeline, fully mocked.

Verifies discover -> ingest -> push wiring via run_sync(), and confirms
discover()/ingest() share a single raw Graph pull (no duplicate calls).
"""
from unittest.mock import MagicMock, patch

from connectors.base.models import HealthStatus
from connectors.microsoft_entra_id.connector import EntraIDConnector


def _connector_with_mock_raw(raw_items):
    connector = EntraIDConnector(auth=MagicMock())
    connector._raw_cache = raw_items
    return connector


def test_discover_and_ingest_share_cached_raw_pull():
    raw_items = [
        {"id": "u1", "displayName": "Alice", "accountEnabled": True, "_object_type": "user"},
        {"id": "u2", "displayName": "Ghost", "accountEnabled": False, "_object_type": "user"},
    ]
    connector = _connector_with_mock_raw(raw_items)

    assets = connector.discover()
    findings = connector.ingest()

    assert len(assets) == 2
    assert len(findings) == 1  # only the disabled user
    assert connector._raw_cache is raw_items  # no re-fetch


@patch("connectors.microsoft_entra_id.connector.discover_raw")
def test_discover_triggers_raw_pull_only_once(mock_discover_raw):
    mock_discover_raw.return_value = [
        {"id": "u1", "displayName": "Alice", "_object_type": "user"}
    ]
    connector = EntraIDConnector(auth=MagicMock())

    connector.discover()
    connector.ingest()

    mock_discover_raw.assert_called_once()


def test_health_check_ok_when_introspect_succeeds():
    connector = EntraIDConnector(auth=MagicMock())
    connector.auth.introspect.return_value = {"value": []}

    status = connector.health_check()

    assert isinstance(status, HealthStatus)
    assert status.ok is True


def test_health_check_fails_on_auth_error():
    from connectors.microsoft_entra_id.auth import EntraIDAuthError

    connector = EntraIDConnector(auth=MagicMock())
    connector.auth.introspect.side_effect = EntraIDAuthError("token invalid")

    status = connector.health_check()

    assert status.ok is False
    assert "token invalid" in status.message


@patch("connectors.microsoft_entra_id.connector.push_to_platform")
def test_run_sync_full_pipeline(mock_push):
    mock_push.return_value = {"assets": 2, "findings": 1}
    raw_items = [
        {"id": "u1", "displayName": "Alice", "accountEnabled": True, "_object_type": "user"},
        {"id": "u2", "displayName": "Ghost", "accountEnabled": False, "_object_type": "user"},
    ]
    connector = _connector_with_mock_raw(raw_items)
    connector.auth.token = MagicMock()

    result = connector.run_sync()

    assert result.status == "success"
    assert result.assets_discovered == 2
    assert result.findings_ingested == 1
    assert result.assets_pushed == 2
    assert result.findings_pushed == 1
