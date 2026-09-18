"""
Reference implementation of Connector, using fake in-memory data.

This is the "one working example connector" deliverable for Week 1.
New connector authors can copy this file as a starting point.
"""

from __future__ import annotations

from typing import Any, Iterable

from .connector import Connector
from .models import Asset, AssetType

# Fake data standing in for a real source system (e.g. a cloud API).
_FAKE_SOURCE_DATA = [
    {"id": "i-0abc123", "name": "web-server-1", "kind": "vm"},
    {"id": "i-0def456", "name": "worker-node-2", "kind": "vm"},
    {"id": "bkt-9f8e7d", "name": "app-uploads", "kind": "bucket"},
]

_KIND_TO_TYPE = {
    "vm": AssetType.COMPUTE,
    "bucket": AssetType.STORAGE,
}


class SampleConnector(Connector):
    """A minimal, fully working connector against fake data.

    Real connectors (AWS, Okta, Splunk, ...) follow this exact shape --
    only discover()/ingest()/check_health() change to talk to a real API.
    """

    name = "sample"

    def __init__(self, simulate_failure: bool = False) -> None:
        self._simulate_failure = simulate_failure
        self._pushed_assets: list[Asset] = []  # stand-in for the platform's asset store

    def discover(self) -> Iterable[Asset]:
        return [
            Asset(
                id=item["id"],
                source=self.name,
                type=_KIND_TO_TYPE.get(item["kind"], AssetType.OTHER),
                name=item["name"],
                raw=item,
            )
            for item in _FAKE_SOURCE_DATA
        ]

    def ingest(self, assets: Iterable[Asset]) -> int:
        if self._simulate_failure:
            raise ConnectionError("simulated push failure")
        assets = list(assets)
        self._pushed_assets.extend(assets)
        return len(assets)

    def check_health(self) -> bool:
        # A real connector would ping its API here.
        return not self._simulate_failure

    def describe_config(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "region": {"type": "string", "description": "Fake region, unused"},
            },
            "required": [],
        }

    def describe_credentials(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "api_key": {"type": "string", "secret": True},
            },
            "required": ["api_key"],
        }
