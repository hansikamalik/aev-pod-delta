"""Sandbox integration test: run the connector against a mock ServiceNow API.

Runs only when MOCK_SN_BASE_URL is set (e.g. pointing at the Week-2
Python sandbox v2 mock server). Exercises the full pipeline without
touching a real ServiceNow instance:

    MOCK_SN_BASE_URL=http://localhost:9001 pytest tests/integration -v
"""

import os

import pytest
import requests

from connectors.servicenow.connector import ServiceNowConnector

pytestmark = pytest.mark.skipif(
    not os.environ.get("MOCK_SN_BASE_URL"), reason="sandbox not available"
)


@pytest.fixture()
def connector():
    cfg = {
        "instance_url": os.environ["MOCK_SN_BASE_URL"],
        "auth": {"method": "basic", "username": "mock", "password": "mock"},
        "vault": {"enabled": False},
        "tables": {"cmdb_ci": "cmdb_ci", "incident": "incident"},
        "push": {"asset_url": "http://localhost:9001/mock/assets",
                 "exposure_url": "http://localhost:9001/mock/exposures"},
    }
    return ServiceNowConnector(config=cfg)


def test_health_check(connector):
    result = connector.health_check()
    assert result["overall_ok"], result


def test_full_sync_pipeline(connector):
    discovery = connector.discover()
    assert discovery.estimated_counts.get("cmdb_ci", 0) >= 1
    raw = connector.ingest()
    normalized = list(connector.normalize(raw))
    assets = [r for r in normalized if "title" not in r]
    findings = [r for r in normalized if "title" in r]
    assert assets and findings
    stats = connector.push(iter(normalized))
    assert stats["assets"]["failed"] == 0
    assert stats["findings"]["failed"] == 0
