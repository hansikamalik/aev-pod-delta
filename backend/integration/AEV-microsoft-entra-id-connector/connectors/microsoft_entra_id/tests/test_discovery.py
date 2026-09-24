"""Tests for Entra ID discovery (Graph pagination across object types)."""
from unittest.mock import MagicMock

from connectors.microsoft_entra_id.discovery import discover_raw


def _mock_auth():
    auth = MagicMock()
    auth.headers.return_value = {"Authorization": "Bearer x"}
    return auth


def test_discover_raw_paginates_and_tags_object_types():
    auth = _mock_auth()
    session = MagicMock()

    users_page1 = {
        "value": [{"id": "u1", "displayName": "Alice"}],
        "@odata.nextLink": "https://graph.microsoft.com/v1.0/users?$top=100&skip=100",
    }
    users_page2 = {"value": [{"id": "u2", "displayName": "Bob"}]}
    groups = {"value": [{"id": "g1", "displayName": "Admins"}]}
    sps = {"value": [{"id": "sp1", "displayName": "CI Pipeline"}]}

    session.get.side_effect = [
        MagicMock(status_code=200, json=lambda: users_page1),
        MagicMock(status_code=200, json=lambda: users_page2),
        MagicMock(status_code=200, json=lambda: groups),
        MagicMock(status_code=200, json=lambda: sps),
    ]
    auth.session = session

    items = discover_raw(auth)

    assert len(items) == 4
    types = {item["_object_type"] for item in items}
    assert types == {"user", "group", "service_principal"}


def test_discover_raw_raises_on_non_200():
    from connectors.microsoft_entra_id.discovery import EntraIDDiscoveryError
    import pytest

    auth = _mock_auth()
    session = MagicMock()
    session.get.return_value = MagicMock(status_code=403, text="Forbidden")
    auth.session = session

    with pytest.raises(EntraIDDiscoveryError):
        discover_raw(auth)
