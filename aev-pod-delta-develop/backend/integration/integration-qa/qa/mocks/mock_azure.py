"""
Mock Azure API — serves fixture data instead of the real ARM/AAD APIs.

Subramani and Ashwin can also use this mock for development; Bhavesh can test
auth against `mock_auth_response` / `mock_auth_failure` below.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"

#: shape of a valid service-principal credential payload (matches Vault schema)
VALID_SERVICE_PRINCIPAL = {
    "tenant_id": "11111111-1111-1111-1111-111111111111",
    "client_id": "22222222-2222-2222-2222-222222222222",
    "client_secret": "dummy-secret-do-not-use",
    "subscription_id": "33333333-3333-3333-3333-333333333333",
}


def _load(filename: str) -> List[Dict[str, Any]]:
    with open(FIXTURE_DIR / filename, encoding="utf-8") as fh:
        return json.load(fh)


def mock_vms() -> List[Dict[str, Any]]:
    return _load("azure_vm.json")


def mock_storage() -> List[Dict[str, Any]]:
    return _load("azure_storage.json")


def mock_aad() -> List[Dict[str, Any]]:
    return _load("azure_aad.json")


def mock_sql() -> List[Dict[str, Any]]:
    return _load("azure_sql.json")


def mock_functions() -> List[Dict[str, Any]]:
    return _load("azure_functions.json")


def mock_all_resources() -> Dict[str, List[Dict[str, Any]]]:
    return {
        "vm": mock_vms(),
        "storage": mock_storage(),
        "aad": mock_aad(),
        "sql": mock_sql(),
        "function": mock_functions(),
    }


class MockAzureAPI:
    """Drop-in stand-in for the real Azure client, with injectable failures."""

    def __init__(self, fail_on: str | None = None) -> None:
        self.fail_on = fail_on  # e.g. "vm", "sql" -> that page raises

    def list_resources(self, resource_type: str, page: int = 0, page_size: int = 2):
        if self.fail_on == resource_type:
            raise RuntimeError(f"mock ARM 500 for {resource_type}")
        data = mock_all_resources()[resource_type]
        start = page * page_size
        yield data[start : start + page_size], len(data)
