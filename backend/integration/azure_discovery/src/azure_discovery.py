"""
Azure Asset Discovery Engine
Owner: Subramani
Deliverable: Complete Azure Discovery Engine (VMs, Storage, AAD, SQL, Functions)

Design notes:
- Built against a MOCK Azure API client (see mock_azure_api.py) so this module
  never blocks on Bhavesh's real authentication module. It only needs a
  credential-shaped object with a `.token` attribute.
- Every resource-type discoverer implements pagination and retries on
  transient API errors, and raises typed exceptions on non-retryable errors.
- Output is a list of plain dicts (raw Azure shape) — normalization into the
  Common Asset schema is intentionally left to Ashwin's module.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Iterator, List, Optional

logger = logging.getLogger("azure_discovery")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class AzureDiscoveryError(Exception):
    """Base class for all discovery errors."""


class AzureApiTransientError(AzureDiscoveryError):
    """Retryable error: throttling (429), 5xx, timeouts."""


class AzureApiFatalError(AzureDiscoveryError):
    """Non-retryable error: 401/403/404, malformed payloads."""


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class DiscoveryConfig:
    page_size: int = 50
    max_retries: int = 3
    backoff_base_seconds: float = 0.5
    resource_types: List[str] = field(
        default_factory=lambda: ["vm", "storage", "aad", "sql", "functions"]
    )


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------

def _with_retries(fn: Callable, config: DiscoveryConfig, context: str):
    attempt = 0
    while True:
        try:
            return fn()
        except AzureApiTransientError as exc:
            attempt += 1
            if attempt > config.max_retries:
                logger.error("Giving up on %s after %d attempts: %s", context, attempt, exc)
                raise
            sleep_for = config.backoff_base_seconds * (2 ** (attempt - 1))
            logger.warning(
                "Transient error in %s (attempt %d/%d): %s — retrying in %.2fs",
                context, attempt, config.max_retries, exc, sleep_for,
            )
            time.sleep(sleep_for)
        except AzureApiFatalError:
            logger.error("Fatal error in %s — not retrying", context)
            raise


# ---------------------------------------------------------------------------
# Pagination helper
# ---------------------------------------------------------------------------

def _paginate(api_client, list_method: str, config: DiscoveryConfig, **params) -> Iterator[dict]:
    """
    Generic pager. Expects api_client.<list_method>(page_size, continuation_token)
    to return a dict: {"items": [...], "continuation_token": str|None}
    """
    continuation_token: Optional[str] = None
    page_num = 0
    while True:
        page_num += 1

        def _call():
            method = getattr(api_client, list_method)
            return method(page_size=config.page_size, continuation_token=continuation_token, **params)

        page = _with_retries(_call, config, context=f"{list_method} page {page_num}")

        items = page.get("items", [])
        logger.info("%s: fetched page %d with %d items", list_method, page_num, len(items))
        for item in items:
            yield item

        continuation_token = page.get("continuation_token")
        if not continuation_token:
            break


# ---------------------------------------------------------------------------
# Per-resource-type discoverers
# ---------------------------------------------------------------------------

def discover_vms(api_client, config: DiscoveryConfig) -> List[dict]:
    return list(_paginate(api_client, "list_virtual_machines", config))


def discover_storage_accounts(api_client, config: DiscoveryConfig) -> List[dict]:
    return list(_paginate(api_client, "list_storage_accounts", config))


def discover_aad_objects(api_client, config: DiscoveryConfig) -> List[dict]:
    return list(_paginate(api_client, "list_aad_objects", config))


def discover_sql_databases(api_client, config: DiscoveryConfig) -> List[dict]:
    return list(_paginate(api_client, "list_sql_databases", config))


def discover_functions(api_client, config: DiscoveryConfig) -> List[dict]:
    return list(_paginate(api_client, "list_function_apps", config))


_DISCOVERER_MAP = {
    "vm": discover_vms,
    "storage": discover_storage_accounts,
    "aad": discover_aad_objects,
    "sql": discover_sql_databases,
    "functions": discover_functions,
}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class AzureDiscoveryEngine:
    """
    Top-level entry point. Takes any api_client that implements the
    list_* methods used above (mock or real — real client is a drop-in
    replacement once Bhavesh's auth module lands, since this engine only
    consumes the client, never builds it).
    """

    def __init__(self, api_client, config: Optional[DiscoveryConfig] = None):
        self.api_client = api_client
        self.config = config or DiscoveryConfig()

    def discover(self) -> dict:
        """Run discovery across all configured resource types.

        Returns a dict keyed by resource type. A failure in one resource
        type does not abort discovery of the others; failures are collected
        under the "errors" key.
        """
        results: dict = {}
        errors: dict = {}

        for resource_type in self.config.resource_types:
            discoverer = _DISCOVERER_MAP.get(resource_type)
            if discoverer is None:
                errors[resource_type] = f"Unknown resource type: {resource_type}"
                continue
            try:
                results[resource_type] = discoverer(self.api_client, self.config)
            except AzureDiscoveryError as exc:
                logger.error("Discovery failed for %s: %s", resource_type, exc)
                errors[resource_type] = str(exc)
                results[resource_type] = []

        if errors:
            results["errors"] = errors
        return results

    def discover_one(self, resource_type: str) -> List[dict]:
        discoverer = _DISCOVERER_MAP.get(resource_type)
        if discoverer is None:
            raise AzureApiFatalError(f"Unknown resource type: {resource_type}")
        return discoverer(self.api_client, self.config)
