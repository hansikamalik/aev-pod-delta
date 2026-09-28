"""
Endpoint-level tests for mock_server/server.py using FastAPI's TestClient
(in-process, no real socket). These test the mock server as its own
piece of software -- separate from whether any particular connector
handles its responses correctly (see test_reference_connector.py).
"""
from __future__ import annotations

import pytest


def test_health_returns_ok(api_client):
    resp = api_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_success_scenario_returns_two_assets(api_client):
    resp = api_client.get("/api/assets", params={"scenario": "success"})
    assert resp.status_code == 200
    body = resp.json()
    assert "assets" in body
    assert len(body["assets"]) == 2
    for asset in body["assets"]:
        assert {"id", "name", "type"} <= asset.keys()


def test_default_scenario_is_success(api_client):
    """No ?scenario= at all should behave the same as scenario=success."""
    with_param = api_client.get("/api/assets", params={"scenario": "success"})
    without_param = api_client.get("/api/assets")
    assert without_param.status_code == 200
    assert without_param.json() == with_param.json()


def test_empty_scenario_returns_no_assets(api_client):
    resp = api_client.get("/api/assets", params={"scenario": "empty"})
    assert resp.status_code == 200
    assert resp.json() == {"assets": []}


def test_malformed_scenario_returns_broken_shapes(api_client):
    resp = api_client.get("/api/assets", params={"scenario": "malformed"})
    assert resp.status_code == 200
    assets = resp.json()["assets"]
    assert assets, "malformed scenario should still return something to malform"
    # At least one asset should be missing a field a well-formed one would have.
    assert any("name" not in a for a in assets)


@pytest.mark.parametrize(
    "scenario,expected_status",
    [
        ("unauthorized", 401),
        ("forbidden", 403),
        ("rate_limited", 429),
        ("server_error", 500),
    ],
)
def test_error_scenarios_return_the_right_status_code(api_client, scenario, expected_status):
    resp = api_client.get("/api/assets", params={"scenario": scenario})
    assert resp.status_code == expected_status


def test_unknown_scenario_returns_400(api_client):
    resp = api_client.get("/api/assets", params={"scenario": "totally-not-a-real-scenario"})
    assert resp.status_code == 400


def test_timeout_scenario_actually_delays(api_client):
    """
    Sanity check on the fixture itself: TestClient calls are synchronous
    and in-process, so this just confirms the delay code path runs
    without raising -- the actual timeout *behavior* is tested against a
    real client in test_reference_connector.py, where a real socket
    timeout can fire.
    """
    import time

    started = time.monotonic()
    resp = api_client.get("/api/assets", params={"scenario": "timeout"})
    elapsed = time.monotonic() - started

    assert resp.status_code == 200
    assert elapsed >= 1.5, "timeout scenario should have delayed the response"