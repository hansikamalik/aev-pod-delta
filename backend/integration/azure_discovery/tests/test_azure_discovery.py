import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from azure_discovery import (
    AzureApiFatalError,
    AzureDiscoveryEngine,
    DiscoveryConfig,
    discover_vms,
)
from mock_azure_api import MockAzureApiClient


def test_discover_vms_returns_all_pages():
    client = MockAzureApiClient(dataset_sizes={"vm": 130, "storage": 1, "aad": 1, "sql": 1, "functions": 1})
    config = DiscoveryConfig(page_size=50)
    vms = discover_vms(client, config)
    assert len(vms) == 130
    assert vms[0]["name"] == "Microsoft.Compute/virtualMachines-000"
    assert vms[-1]["name"] == "Microsoft.Compute/virtualMachines-129"


def test_discover_all_resource_types():
    client = MockAzureApiClient()
    engine = AzureDiscoveryEngine(client)
    results = engine.discover()
    for rtype in ["vm", "storage", "aad", "sql", "functions"]:
        assert rtype in results
        assert len(results[rtype]) > 0
    assert "errors" not in results


def test_retries_on_transient_throttling():
    # Fails every 2nd page call, engine should retry and still get all data.
    client = MockAzureApiClient(dataset_sizes={"vm": 100}, fail_every_n_pages=2)
    config = DiscoveryConfig(page_size=25, backoff_base_seconds=0.001)
    vms = discover_vms(client, config)
    assert len(vms) == 100


def test_fatal_auth_error_is_not_retried():
    client = MockAzureApiClient(credentials=None)
    config = DiscoveryConfig(max_retries=5)
    with pytest.raises(AzureApiFatalError):
        discover_vms(client, config)


def test_unknown_resource_type_raises():
    client = MockAzureApiClient()
    engine = AzureDiscoveryEngine(client)
    with pytest.raises(AzureApiFatalError):
        engine.discover_one("not_a_real_type")


def test_partial_failure_isolated_per_resource_type():
    client = MockAzureApiClient(credentials=None)
    engine = AzureDiscoveryEngine(client, DiscoveryConfig(max_retries=0))
    results = engine.discover()
    assert "errors" in results
    for rtype in ["vm", "storage", "aad", "sql", "functions"]:
        assert results[rtype] == []
        assert rtype in results["errors"]
