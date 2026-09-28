"""
Tests for scenarios/scenario_loader.py -- this is the part everything
else depends on, so it gets tested on its own before anything is layered
on top of it.
"""
from __future__ import annotations

from scenarios.scenario_loader import load_scenarios


REQUIRED_SCENARIOS = {
    "success": 200,
    "empty": 200,
    "malformed": 200,
    "unauthorized": 401,
    "forbidden": 403,
    "rate_limited": 429,
    "server_error": 500,
}


def test_load_scenarios_returns_a_dict():
    scenarios = load_scenarios()
    assert isinstance(scenarios, dict)
    assert scenarios, "scenarios.yaml loaded but produced no scenarios"


def test_all_required_scenarios_are_present():
    scenarios = load_scenarios()
    missing = set(REQUIRED_SCENARIOS) - set(scenarios)
    assert not missing, f"scenarios.yaml is missing: {missing}"


def test_each_scenario_has_the_expected_status_code():
    scenarios = load_scenarios()
    for name, expected_status in REQUIRED_SCENARIOS.items():
        assert scenarios[name]["status_code"] == expected_status, (
            f"scenario '{name}' has status_code "
            f"{scenarios[name]['status_code']!r}, expected {expected_status!r}"
        )


def test_timeout_scenario_declares_a_delay():
    scenarios = load_scenarios()
    assert "timeout" in scenarios, "no 'timeout' scenario defined"
    assert scenarios["timeout"].get("delay_seconds", 0) > 0, (
        "'timeout' scenario exists but doesn't actually delay the response "
        "-- it can't be used to test client-side timeout handling"
    )