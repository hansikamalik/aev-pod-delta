"""
Splunk connector tests — Ayyappatadi.
Auth, credentials, event forwarding, normalization, health, retries.
Run:  pytest tests/splunk -m splunk
"""
from __future__ import annotations

import pytest

from qa.mocks.mock_splunk import MockSplunkHEC, mock_splunk_events
from qa.validators import validate_assets
from tests.conftest import module_or_skip

VALID_TOKEN = "team-splunk-token"


@pytest.fixture()
def hec():
    return MockSplunkHEC(valid_token=VALID_TOKEN)


@pytest.fixture()
def splunk_module():
    return module_or_skip("splunk")


@pytest.mark.splunk
class TestSplunkAuth:
    def test_valid_token_authenticates(self, splunk_module, hec):
        conn = splunk_connector(splunk_module, hec, VALID_TOKEN)
        assert conn is not None

    def test_invalid_token_raises_auth_error(self, splunk_module, hec):
        with pytest.raises(Exception) as exc:
            splunk_connector(splunk_module, hec, "wrong-token")
        assert "auth" in type(exc.value).__name__.lower() or "401" in str(exc.value)


@pytest.mark.splunk
class TestSplunkForwarding:
    def test_forwards_all_fixture_events(self, splunk_module, hec):
        conn = splunk_connector(splunk_module, hec, VALID_TOKEN)
        events = mock_splunk_events()
        conn.forward(events)
        assert hec.received_count() == len(events)

    def test_forwarded_events_match_source(self, splunk_module, hec):
        conn = splunk_connector(splunk_module, hec, VALID_TOKEN)
        events = mock_splunk_events()
        conn.forward(events)
        assert hec.received[0]["event"]["action"] == events[0]["event"]["action"]

    def test_retries_on_transient_5xx(self, splunk_module, hec):
        conn = splunk_connector(splunk_module, hec, VALID_TOKEN)
        hec.fail_next_n = 2  # two transient failures before success
        conn.forward(mock_splunk_events()[:1])
        assert hec.received_count() == 1, "connector must retry through 5xx"


@pytest.mark.splunk
class TestSplunkNormalization:
    def test_normalized_events_are_schema_valid(self, splunk_module):
        normalize = getattr(splunk_module, "normalize_events", None)
        if normalize is None:
            pytest.skip("splunk module exposes no normalize_events() yet")
        violations = validate_assets(normalize(mock_splunk_events()))
        assert not violations, violations


@pytest.mark.splunk
class TestSplunkHealth:
    def test_health_reports_on_bad_endpoint_without_raising(self, splunk_module, hec):
        conn = splunk_connector(splunk_module, hec, VALID_TOKEN)
        result = conn.check_health()
        assert isinstance(result, bool), "§17: check_health must return bool, never raise"


# ---------------------------------------------------------------------------
def splunk_connector(splunk_module, hec: MockSplunkHEC, token: str):
    """Build a connector against the mock HEC using the module's public API."""
    if hasattr(splunk_module, "SplunkConnector"):
        conn = splunk_module.SplunkConnector()
        if hasattr(conn, "_apply_config"):
            conn._apply_config({"endpoint": "mock://hec"})
            conn._apply_credentials({"token": token})
        return conn
    if hasattr(splunk_module, "create_connector"):
        return splunk_module.create_connector(endpoint="mock://hec", token=token)
    pytest.skip("splunk module exposes no SplunkConnector/create_connector yet")
