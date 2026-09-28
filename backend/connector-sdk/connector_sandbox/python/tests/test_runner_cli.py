"""
Tests for sandbox/runner.py's run_connector() -- the piece the CLI's
__main__ block calls. Not testing the argparse wiring itself since that's
just stdlib plumbing; this checks the actual reporting logic.
"""
from __future__ import annotations

from connector_sdk import SyncStatus
from connectors.reference.connector import ReferenceConnector
from sandbox.runner import run_connector


def _connector(live_server, scenario):
    return ReferenceConnector(
        base_url=live_server,
        api_key="test-key-do-not-use-in-prod",
        extra_params={"scenario": scenario},
    )


def test_run_connector_reports_success(live_server, capsys):
    result = run_connector(_connector(live_server, "success"), scenario="success")
    out = capsys.readouterr().out

    assert result.status == SyncStatus.SUCCESS
    assert "Status: SyncStatus.SUCCESS" in out or "Status: success" in out
    assert "Assets discovered: 2" in out
    assert "Assets pushed: 2" in out
    assert "Errors:" not in out


def test_run_connector_reports_failure_and_lists_errors(live_server, capsys):
    result = run_connector(_connector(live_server, "unauthorized"), scenario="unauthorized")
    out = capsys.readouterr().out

    assert result.status == SyncStatus.FAILED
    assert "Errors:" in out
    assert "discover() failed" in out


def test_run_connector_returns_the_sync_result(live_server):
    """run_connector should hand back the SyncResult, not just print it --
    callers (including future CLI features) need the structured result."""
    result = run_connector(_connector(live_server, "success"), scenario="success")
    assert result.assets_discovered == 2
    assert result.assets_pushed == 2

# ---- main(): the CLI wiring that the tests above don't touch ----------------

def test_main_returns_zero_on_a_successful_scenario(live_server, capsys):
    from sandbox.runner import main

    rc = main(["--connector", "reference", "--scenario", "success", "--base-url", live_server])
    assert rc == 0
    assert "Assets discovered: 2" in capsys.readouterr().out


def test_main_returns_nonzero_on_a_failing_scenario(live_server):
    from sandbox.runner import main

    assert main(["--scenario", "unauthorized", "--base-url", live_server]) == 1
