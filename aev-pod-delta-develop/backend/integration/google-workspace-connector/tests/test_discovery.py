from unittest.mock import MagicMock

from google_workspace_connector.discovery import GoogleWorkspaceDiscovery


def _mock_authenticator(directory_pages=None, reports_pages=None):
    authenticator = MagicMock()

    if directory_pages is not None:
        directory_service = MagicMock()
        directory_service.users.return_value.list.return_value.execute.side_effect = directory_pages
        authenticator.get_directory_service.return_value = directory_service

    if reports_pages is not None:
        reports_service = MagicMock()
        reports_service.activities.return_value.list.return_value.execute.side_effect = reports_pages
        authenticator.get_reports_service.return_value = reports_service

    return authenticator


def test_discover_paginates_through_all_users():
    pages = [
        {"users": [{"id": "1"}, {"id": "2"}], "nextPageToken": "page-2"},
        {"users": [{"id": "3"}], "nextPageToken": None},
    ]
    authenticator = _mock_authenticator(directory_pages=pages)
    discovery = GoogleWorkspaceDiscovery(authenticator)

    users = discovery.discover()

    assert [u["id"] for u in users] == ["1", "2", "3"]


def test_discover_handles_single_page():
    pages = [{"users": [{"id": "1"}]}]  # no nextPageToken at all
    authenticator = _mock_authenticator(directory_pages=pages)
    discovery = GoogleWorkspaceDiscovery(authenticator)

    users = discovery.discover()

    assert len(users) == 1


def test_discover_handles_empty_result():
    pages = [{}]  # tenant with zero users
    authenticator = _mock_authenticator(directory_pages=pages)
    discovery = GoogleWorkspaceDiscovery(authenticator)

    assert discovery.discover() == []


def test_ingest_paginates_through_all_activities():
    pages = [
        {"items": [{"id": {"uniqueQualifier": "a"}}], "nextPageToken": "page-2"},
        {"items": [{"id": {"uniqueQualifier": "b"}}], "nextPageToken": None},
    ]
    authenticator = _mock_authenticator(reports_pages=pages)
    discovery = GoogleWorkspaceDiscovery(authenticator)

    activities = discovery.ingest()

    assert len(activities) == 2


def test_ingest_handles_empty_result():
    authenticator = _mock_authenticator(reports_pages=[{}])
    discovery = GoogleWorkspaceDiscovery(authenticator)

    assert discovery.ingest() == []
