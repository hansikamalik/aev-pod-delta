"""
Mock Azure API client used for independent development/testing.
Simulates pagination, throttling, and transient/fatal failures so
discovery logic (retries, pagination, error handling) can be fully
exercised without a real Azure subscription or Bhavesh's live auth module.
"""

from __future__ import annotations

import random
from typing import List, Optional

from azure_discovery import AzureApiFatalError, AzureApiTransientError


def _fake_resources(prefix: str, count: int) -> List[dict]:
    return [
        {
            "id": f"/subscriptions/mock-sub/resourceGroups/rg-mock/providers/{prefix}/{prefix}-{i:03d}",
            "name": f"{prefix}-{i:03d}",
            "type": prefix,
            "location": "eastus",
            "tags": {"env": "mock"},
        }
        for i in range(count)
    ]


class MockAzureApiClient:
    """
    Deterministic-by-default mock with optional fault injection.

    Args:
        dataset_sizes: number of fake resources to generate per type.
        fail_every_n_pages: if set, every Nth page request raises a
            transient error once (to exercise retry logic).
        credentials: any object with a truthy value stands in for a
            validated credential; None simulates missing auth (fatal).
    """

    def __init__(
        self,
        dataset_sizes: Optional[dict] = None,
        fail_every_n_pages: Optional[int] = None,
        credentials: object = "mock-token",
    ):
        self.credentials = credentials
        self.fail_every_n_pages = fail_every_n_pages
        self._call_count = 0

        defaults = {
            "vm": 130,
            "storage": 45,
            "aad": 210,
            "sql": 12,
            "functions": 60,
        }
        sizes = {**defaults, **(dataset_sizes or {})}
        self._data = {
            "vm": _fake_resources("Microsoft.Compute/virtualMachines", sizes["vm"]),
            "storage": _fake_resources("Microsoft.Storage/storageAccounts", sizes["storage"]),
            "aad": _fake_resources("Microsoft.AAD/objects", sizes["aad"]),
            "sql": _fake_resources("Microsoft.Sql/servers/databases", sizes["sql"]),
            "functions": _fake_resources("Microsoft.Web/sites/functions", sizes["functions"]),
        }

    def _check_auth(self):
        if not self.credentials:
            raise AzureApiFatalError("401 Unauthorized: missing or invalid credentials")

    def _maybe_inject_failure(self):
        self._call_count += 1
        if self.fail_every_n_pages and self._call_count % self.fail_every_n_pages == 0:
            raise AzureApiTransientError("429 Too Many Requests: throttled by Azure API")

    def _list(self, resource_type: str, page_size: int, continuation_token: Optional[str]) -> dict:
        self._check_auth()
        self._maybe_inject_failure()

        dataset = self._data[resource_type]
        start = int(continuation_token) if continuation_token else 0
        end = start + page_size
        page_items = dataset[start:end]
        next_token = str(end) if end < len(dataset) else None
        return {"items": page_items, "continuation_token": next_token}

    # Public API surface expected by azure_discovery.py --------------------

    def list_virtual_machines(self, page_size, continuation_token=None):
        return self._list("vm", page_size, continuation_token)

    def list_storage_accounts(self, page_size, continuation_token=None):
        return self._list("storage", page_size, continuation_token)

    def list_aad_objects(self, page_size, continuation_token=None):
        return self._list("aad", page_size, continuation_token)

    def list_sql_databases(self, page_size, continuation_token=None):
        return self._list("sql", page_size, continuation_token)

    def list_function_apps(self, page_size, continuation_token=None):
        return self._list("functions", page_size, continuation_token)
