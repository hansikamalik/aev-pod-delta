
"""
Integration tests for ReferenceConnector against the real mock server,
running on a real localhost port (see `live_server` in conftest.py).

Covers both direct method calls and sync(), since their error-handling
behavior differs.
"""
from __future__ import annotations

import httpx
import pytest

from connector_sdk import AssetType, Connector, SyncStatus
from connectors.reference.connector import ReferenceConnector


def make_connector(live_server, scenario="success", **kwargs):
    return ReferenceConnector(
        base_url=live_server,
        api_key="test-key-do-not-use-in-prod",
        extra_params={"scenario": scenario},
        **kwargs,
    )


# ---- success ---------------------------------------------------------


def test_discover_normalizes_the_success_payload(live_server):
    connector = make_connector(live_server, "success")
    assets = list(connector.discover())

    assert len(assets) == 2
    for asset in assets:
        assert asset.source == "reference"
        assert asset.type == AssetType.COMPUTE
        assert asset.raw


def test_describe_config_and_credentials_have_valid_schema_shapes():
    connector = ReferenceConnector(
        base_url="http://127.0.0.1:8080",
        api_key="test-key-do-not-use-in-prod",
    )

    config = connector.describe_config()
    credentials = connector.describe_credentials()

    # Config schema
    assert config["type"] == "object"
    assert isinstance(config["properties"], dict)
    assert "base_url" in config["properties"]
    assert config["required"] == ["base_url"]

    # Credential schema
    assert credentials["type"] == "object"
    assert isinstance(credentials["properties"], dict)
    assert "api_key" in credentials["properties"]
    assert credentials["required"] == ["api_key"]

def test_full_sync_succeeds_on_the_success_scenario(live_server):
    connector = make_connector(live_server, "success")
    result = connector.sync()

    assert result.status == SyncStatus.SUCCESS
    assert result.assets_discovered == 2
    assert result.assets_pushed == 2
    assert result.errors == []


def test_sync_reports_ingest_failure(live_server):
    """An ingest exception should be captured and reported by sync()."""

    class FailingIngestConnector(ReferenceConnector):
        def ingest(self, assets):
            raise RuntimeError("simulated ingest failure")

    connector = FailingIngestConnector(
        base_url=live_server,
        api_key="test-key-do-not-use-in-prod",
        extra_params={"scenario": "success"},
    )

    result = connector.sync()

    assert result.status == SyncStatus.FAILED
    assert result.assets_discovered == 2
    assert result.assets_pushed == 0
    assert any("ingest() failed" in error for error in result.errors)


# ---- abstract contract / invalid connector ---------------------------


def test_invalid_connector_cannot_be_instantiated():
    """A subclass missing abstract methods must not be instantiable."""

    class InvalidConnector(Connector):
        name = "invalid"

        # Intentionally omit all abstract methods.

    with pytest.raises(TypeError, match="abstract"):
        InvalidConnector()


# ---- empty ------------------------------------------------------------


def test_discover_returns_empty_list_on_empty_scenario(live_server):
    connector = make_connector(live_server, "empty")
    assert list(connector.discover()) == []


def test_sync_still_succeeds_with_zero_assets(live_server):
    """An empty discovery result is successful; ingest() is skipped."""
    connector = make_connector(live_server, "empty")
    result = connector.sync()

    assert result.status == SyncStatus.SUCCESS
    assert result.assets_discovered == 0
    assert result.assets_pushed == 0
    assert result.errors == []
    assert connector._pushed_assets == []


# ---- malformed -------------------------------------------------------


def test_discover_raises_directly_on_malformed_response(live_server):
    """Direct discovery currently propagates KeyError for missing fields."""
    connector = make_connector(live_server, "malformed")

    with pytest.raises(KeyError):
        list(connector.discover())


def test_sync_reports_malformed_response_as_a_failure(live_server):
    connector = make_connector(live_server, "malformed")
    result = connector.sync()

    assert result.status == SyncStatus.FAILED
    assert result.assets_discovered == 0
    assert result.assets_pushed == 0
    assert any("discover() failed" in error for error in result.errors)


# ---- HTTP error scenarios --------------------------------------------


@pytest.mark.parametrize(
    "scenario,expected_status",
    [
        ("unauthorized", 401),
        ("forbidden", 403),
        ("rate_limited", 429),
        ("server_error", 500),
    ],
)
def test_discover_raises_on_http_errors(live_server, scenario, expected_status):
    connector = make_connector(live_server, scenario)

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        list(connector.discover())

    assert exc_info.value.response.status_code == expected_status


@pytest.mark.parametrize(
    "scenario",
    ["unauthorized", "forbidden", "rate_limited", "server_error"],
)
def test_sync_reports_http_errors_as_failures_not_crashes(live_server, scenario):
    connector = make_connector(live_server, scenario)
    result = connector.sync()

    assert result.status == SyncStatus.FAILED
    assert result.assets_pushed == 0
    assert any("discover() failed" in error for error in result.errors)


# ---- timeout ---------------------------------------------------------


def test_discover_raises_timeout_when_server_is_slow(live_server):
    connector = make_connector(live_server, "timeout", timeout=0.3)

    with pytest.raises(httpx.TimeoutException):
        list(connector.discover())


def test_sync_reports_timeout_as_a_failure_not_a_hang(live_server):
    connector = make_connector(live_server, "timeout", timeout=0.3)
    result = connector.sync()

    assert result.status == SyncStatus.FAILED
    assert any("discover() failed" in error for error in result.errors)


# ---- check_health ----------------------------------------------------


def test_check_health_true_when_server_is_up(live_server):
    connector = make_connector(live_server, "success")
    assert connector.check_health() is True


def test_check_health_false_when_server_is_unreachable():
    connector = ReferenceConnector(
        base_url="http://127.0.0.1:1",
        api_key="test-key",
        timeout=0.5,
    )

    assert connector.check_health() is False


def test_check_health_does_not_raise_on_timeout(live_server):
    import time

    connector = make_connector(live_server, "timeout", timeout=1.0)
    started = time.monotonic()

    assert connector.check_health() is True
    assert time.monotonic() - started < 1.0
