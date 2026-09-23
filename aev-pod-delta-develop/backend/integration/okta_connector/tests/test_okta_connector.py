"""
Tests for the Okta connector.

Unit tests mock the Okta HTTP API directly (no real network calls).
The integration test spins up OktaConnector against a fake OktaClient to
prove discover -> normalize -> push works end to end, matching the
Week 3 "Integration testing" line item.
"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from okta_connector.client import OktaAPIError, OktaClient
from okta_connector.connector import OktaConnector
from okta_connector.credentials import OktaCredentials
from okta_connector.models import AssetStatus, AssetType


# ---- fixtures ---------------------------------------------------------

@pytest.fixture
def credentials() -> OktaCredentials:
    return OktaCredentials(org_url="https://example.okta.com", api_token="fake-token-123")


SAMPLE_USER = {
    "id": "00u1abc",
    "status": "ACTIVE",
    "created": "2024-01-01T00:00:00.000Z",
    "lastLogin": "2026-08-01T00:00:00.000Z",
    "profile": {
        "firstName": "Priya",
        "lastName": "Nair",
        "login": "priya.nair@example.com",
        "email": "priya.nair@example.com",
        "department": "Security",
        "title": "Analyst",
    },
}

SAMPLE_DEPROVISIONED_USER = {
    "id": "00u2def",
    "status": "DEPROVISIONED",
    "profile": {"firstName": "Old", "lastName": "Employee", "login": "old@example.com"},
}

SAMPLE_GROUP = {
    "id": "00g1xyz",
    "type": "OKTA_GROUP",
    "profile": {"name": "Security Analysts", "description": "SOC team"},
}


# ---- credentials / auth ------------------------------------------------

def test_credentials_build_correct_auth_header(credentials):
    header = credentials.auth_header()
    assert header["Authorization"] == "SSWS fake-token-123"
    assert header["Accept"] == "application/json"


def test_credentials_reject_non_https_org_url():
    with pytest.raises(ValueError):
        OktaCredentials(org_url="http://example.okta.com", api_token="x")


def test_credentials_strip_trailing_slash():
    creds = OktaCredentials(org_url="https://example.okta.com/", api_token="x")
    assert creds.org_url == "https://example.okta.com"


# ---- client / pagination -----------------------------------------------

@patch("okta_connector.client.requests.Session.get")
def test_list_users_single_page(mock_get, credentials):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [SAMPLE_USER]
    mock_resp.headers = {}
    mock_get.return_value = mock_resp

    client = OktaClient(credentials)
    users = client.list_users()

    assert users == [SAMPLE_USER]
    mock_get.assert_called_once()


@patch("okta_connector.client.requests.Session.get")
def test_list_users_follows_pagination(mock_get, credentials):
    page1 = MagicMock()
    page1.status_code = 200
    page1.json.return_value = [SAMPLE_USER]
    page1.headers = {"Link": '<https://example.okta.com/api/v1/users?after=abc>; rel="next"'}

    page2 = MagicMock()
    page2.status_code = 200
    page2.json.return_value = [SAMPLE_DEPROVISIONED_USER]
    page2.headers = {}

    mock_get.side_effect = [page1, page2]

    client = OktaClient(credentials)
    users = client.list_users()

    assert len(users) == 2
    assert mock_get.call_count == 2


@patch("okta_connector.client.requests.Session.get")
def test_client_raises_on_error_status(mock_get, credentials):
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Invalid token"
    mock_get.return_value = mock_resp

    client = OktaClient(credentials)
    with pytest.raises(OktaAPIError):
        client.list_users()


def test_health_check_true_on_200(credentials):
    client = OktaClient(credentials)
    client._get = MagicMock(return_value=MagicMock(status_code=200))
    assert client.health_check() is True


def test_health_check_false_on_api_error(credentials):
    client = OktaClient(credentials)
    client._get = MagicMock(side_effect=OktaAPIError("boom"))
    assert client.health_check() is False


# ---- normalization -------------------------------------------------------

def _fake_client(users: List[Dict[str, Any]], groups: List[Dict[str, Any]], members: Dict[str, List[Dict[str, Any]]]):
    client = MagicMock(spec=OktaClient)
    client.list_users.return_value = users
    client.list_groups.return_value = groups
    client.list_group_members.side_effect = lambda gid: members.get(gid, [])
    return client


def test_normalize_maps_active_user_correctly(credentials):
    client = _fake_client([SAMPLE_USER], [], {})
    connector = OktaConnector(credentials, client=client)

    raw = connector.discover()
    assets = connector.normalize(raw)

    assert len(assets) == 1
    asset = assets[0]
    assert asset.asset_type == AssetType.USER
    assert asset.name == "Priya Nair"
    assert asset.status == AssetStatus.ACTIVE
    assert asset.attributes["email"] == "priya.nair@example.com"


def test_normalize_maps_deprovisioned_user_as_inactive(credentials):
    client = _fake_client([SAMPLE_DEPROVISIONED_USER], [], {})
    connector = OktaConnector(credentials, client=client)

    assets = connector.normalize(connector.discover())

    assert assets[0].status == AssetStatus.INACTIVE


def test_normalize_maps_group_with_member_count(credentials):
    client = _fake_client(
        [], [SAMPLE_GROUP], {"00g1xyz": [{"id": "00u1abc"}, {"id": "00u2def"}]}
    )
    connector = OktaConnector(credentials, client=client)

    assets = connector.normalize(connector.discover())

    assert len(assets) == 1
    group_asset = assets[0]
    assert group_asset.asset_type == AssetType.GROUP
    assert group_asset.name == "Security Analysts"
    assert group_asset.attributes["member_count"] == 2
    assert group_asset.attributes["member_ids"] == ["00u1abc", "00u2def"]


# ---- sync / integration ---------------------------------------------------

def test_sync_end_to_end_pushes_normalized_assets(credentials):
    client = _fake_client(
        users=[SAMPLE_USER, SAMPLE_DEPROVISIONED_USER],
        groups=[SAMPLE_GROUP],
        members={"00g1xyz": [{"id": "00u1abc"}]},
    )
    pushed_assets = []

    def fake_push(assets):
        pushed_assets.extend(assets)
        return len(assets)

    connector = OktaConnector(credentials, client=client, push_fn=fake_push)
    result = connector.sync()

    assert result.connector == "okta"
    assert result.assets_discovered == 3  # 2 users + 1 group
    assert result.assets_pushed == 3
    assert result.success is True
    assert len(pushed_assets) == 3


def test_sync_records_error_and_skips_push_on_discover_failure(credentials):
    client = MagicMock(spec=OktaClient)
    client.list_users.side_effect = OktaAPIError("token expired")

    connector = OktaConnector(credentials, client=client)
    result = connector.sync()

    assert result.success is False
    assert result.assets_discovered == 0
    assert result.assets_pushed == 0
    assert "token expired" in result.errors[0]


def test_health_check_delegates_to_client(credentials):
    client = MagicMock(spec=OktaClient)
    client.health_check.return_value = True

    connector = OktaConnector(credentials, client=client)
    assert connector.health_check() is True
    client.health_check.assert_called_once()


def test_describe_config_and_credentials_are_schema_dicts(credentials):
    connector = OktaConnector(credentials, client=MagicMock(spec=OktaClient))
    config_schema = connector.describe_config()
    cred_schema = connector.describe_credentials()

    assert config_schema["type"] == "object"
    assert "sync_interval_minutes" in config_schema["properties"]
    assert cred_schema["required"] == ["org_url", "api_token"]
