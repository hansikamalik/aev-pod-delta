"""
Root pytest configuration — the Day-1 test framework.

Conventions for the whole squad:
  * Tests never import teammates' modules at module scope. Use the
    `module_or_skip` helper so the suite stays GREEN on Day 1 and lights up
    each area as the real module lands.
  * All fixtures live in qa/fixtures/, all mocks in qa/mocks/.
  * Contract tests are the only suite that must always run everywhere.
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))  # make `qa.*` importable from anywhere

DummyConnector = importlib.import_module("qa.mocks.dummy_connector").DummyConnector  # noqa: E402
_mock_vault = importlib.import_module("qa.mocks.mock_vault")
MockVault = _mock_vault.MockVault
seeded_vault = _mock_vault.seeded_vault


# ---------------------------------------------------------------------------
# target-module resolution
# ---------------------------------------------------------------------------
# Map QA area -> teammate module import path. Update these names once Harshal
# finalizes the repo layout; nothing else needs to change.
TARGET_MODULES: Dict[str, str] = {
    "azure.auth": "azure_connector.auth",          # Bhavesh K
    "azure.discovery": "azure_connector.discovery",  # Subramani
    "azure.normalize": "azure_connector.normalize",  # Ashwin
    "azure.push": "azure_connector.push",          # Ashwin
    "splunk": "splunk_connector",                  # Ayyappatadi
    "vault": "infra.vault",                        # Abhiram
    "scheduler": "infra.scheduler",                # Abhiram
    "lock": "infra.distributed_lock",              # Abhiram
}


def module_or_skip(area: str):
    """
    Import a teammate's target module, or pytest.skip with a clear reason.
    Keeps CI green while modules are in flight (Week-1 parallel rule).
    """
    dotted = TARGET_MODULES[area]
    try:
        return importlib.import_module(dotted)
    except ModuleNotFoundError as exc:
        if exc.name and (dotted == exc.name or dotted.startswith(exc.name)):
            pytest.skip(f"{area}: module `{dotted}` not implemented yet")
        raise


# ---------------------------------------------------------------------------
# shared fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def dummy_connector() -> DummyConnector:
    conn = DummyConnector()
    conn._apply_config({"endpoint": "https://mock.internal", "poll_interval": 30})
    conn._apply_credentials({"api_key": "dummy-key-123"})
    return conn


@pytest.fixture()
def vault() -> MockVault:
    return seeded_vault()


@pytest.fixture()
def vault_config() -> Dict[str, Any]:
    """Credential payloads by connector name, as connectors will receive them."""
    return {
        "azure": {
            "tenant_id": "11111111-1111-1111-1111-111111111111",
            "client_id": "22222222-2222-2222-2222-222222222222",
            "client_secret": "dummy-secret-do-not-use",
            "subscription_id": "33333333-3333-3333-3333-333333333333",
        },
        "splunk": {"token": "team-splunk-token"},
        "dummy": {"api_key": "dummy-key-123"},
    }


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "contract: connector contract tests (P0)")
    config.addinivalue_line("markers", "azure: Azure module tests")
    config.addinivalue_line("markers", "splunk: Splunk connector tests")
    config.addinivalue_line("markers", "infra: shared infrastructure tests")
    config.addinivalue_line("markers", "integration: end-to-end suite")
    config.addinivalue_line("markers", "regression: post-integration regression")


def pytest_collection_modifyitems(items):  # auto-mark by directory
    for item in items:
        rel = Path(item.fspath).relative_to(Path(__file__).parent)
        top = rel.parts[0] if rel.parts else ""
        marker = {
            "contract": "contract",
            "azure": "azure",
            "splunk": "splunk",
            "infra": "infra",
            "integration": "integration",
            "regression": "regression",
        }.get(top)
        if marker:
            item.add_marker(marker)
