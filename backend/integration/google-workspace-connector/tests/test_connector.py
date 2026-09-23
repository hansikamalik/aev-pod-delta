from unittest.mock import MagicMock, patch

from google_workspace_connector.base import Asset, SyncResult
from google_workspace_connector.connector import GoogleWorkspaceConnector

RAW_USER = {
    "id": "user-1",
    "primaryEmail": "jane@customer.com",
    "isEnrolledIn2Sv": True,
}

RAW_ACTIVITY = {
    "id": {"uniqueQualifier": "act-1", "time": "2026-09-15T10:00:00Z"},
    "actor": {"email": "admin@customer.com", "profileId": "admin-1"},
    "events": [{"name": "GRANT_ADMIN_PRIVILEGE"}],
}


def _build_connector(auth_ok=True):
    with patch(
        "google_workspace_connector.connector.load_google_workspace_credentials"
    ) as mock_load_creds, patch(
        "google_workspace_connector.connector.GoogleWorkspaceAuthenticator"
    ) as mock_authenticator_cls, patch(
        "google_workspace_connector.connector.GoogleWorkspaceDiscovery"
    ) as mock_discovery_cls, patch(
        "google_workspace_connector.connector.BetaPlatformPusher"
    ) as mock_pusher_cls:
        mock_load_creds.return_value = MagicMock()

        mock_authenticator = MagicMock()
        mock_authenticator.validate.return_value = auth_ok
        mock_authenticator_cls.return_value = mock_authenticator

        mock_discovery = MagicMock()
        mock_discovery.discover.return_value = [RAW_USER]
        mock_discovery.ingest.return_value = [RAW_ACTIVITY]
        mock_discovery_cls.return_value = mock_discovery

        mock_pusher = MagicMock()
        mock_pusher.push.return_value = SyncResult(
            connector="google_workspace",
            started_at="t0",
            finished_at="t1",
            assets_count=1,
            findings_count=0,
            errors=[],
        )
        mock_pusher_cls.return_value = mock_pusher

        connector = GoogleWorkspaceConnector(
            vault=MagicMock(), org_id="org-123", beta_api_token="fake-token"
        )
        return connector, mock_discovery, mock_pusher


def test_authenticate_delegates_to_authenticator():
    connector, _, _ = _build_connector(auth_ok=True)
    assert connector.authenticate() is True


def test_health_check_delegates_to_authenticate():
    connector, _, _ = _build_connector(auth_ok=False)
    assert connector.health_check() is False


def test_discover_returns_raw_users():
    connector, discovery, _ = _build_connector()
    users = connector.discover()

    assert users == [RAW_USER]
    discovery.discover.assert_called_once()


def test_ingest_returns_raw_activities():
    connector, discovery, _ = _build_connector()
    activities = connector.ingest()

    assert activities == [RAW_ACTIVITY]
    discovery.ingest.assert_called_once()


def test_normalize_produces_assets_and_sets_findings():
    connector, _, _ = _build_connector()

    assets = connector.normalize([RAW_USER])

    assert len(assets) == 1
    assert isinstance(assets[0], Asset)
    assert assets[0].external_id == "user-1"
    # normalize() internally calls ingest() to populate findings
    assert len(connector.findings) == 1
    assert connector.findings[0].title == "GRANT_ADMIN_PRIVILEGE"


def test_push_merges_findings_count_into_result():
    connector, _, pusher = _build_connector()
    connector.findings = [MagicMock(), MagicMock()]  # pretend 2 findings

    result = connector.push([Asset(external_id="x", source="google_workspace", asset_type="user", name="x")])

    assert result.findings_count == 2
    pusher.push.assert_called_once()


def test_run_full_sync_short_circuits_on_auth_failure():
    connector, discovery, pusher = _build_connector(auth_ok=False)

    result = connector.run_full_sync()

    assert result.success is False
    assert result.errors == ["Authentication failed"]
    discovery.discover.assert_not_called()
    pusher.push.assert_not_called()


def test_run_full_sync_happy_path():
    connector, discovery, pusher = _build_connector(auth_ok=True)

    result = connector.run_full_sync()

    discovery.discover.assert_called_once()
    pusher.push.assert_called_once()
    assert result.findings_count == 1  # one finding from RAW_ACTIVITY
