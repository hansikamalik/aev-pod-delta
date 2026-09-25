"""Factory used by scripts/connector_cli.py to build a runnable SampleConnector."""

from __future__ import annotations

from connector_sdk.testing import InMemoryPlatformClient

from .client import SampleSourceClient
from .connector import SampleConnector


def build() -> SampleConnector:
    return SampleConnector(
        config={"region": "eastus", "page_size": 50},
        credentials={"api_key": "cli-demo-key"},
        client=SampleSourceClient(api_key="cli-demo-key"),
        platform_client=InMemoryPlatformClient(),
    )
