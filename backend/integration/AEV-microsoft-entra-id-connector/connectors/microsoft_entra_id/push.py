"""Microsoft Entra ID push ΓÇö Week 2 deliverable.

Thin wrapper around the shared PlatformClient (connectors/base/platform.py).
Kept as its own module ΓÇö matching the sibling connectors' layout ΓÇö so the
connector.py orchestration stays simple and this piece is independently
testable/mockable.
"""
from __future__ import annotations

from connectors.base.models import Asset, Finding
from connectors.base.platform import PlatformClient


def push_to_platform(assets: list[Asset], findings: list[Finding],
                      client: PlatformClient | None = None) -> dict:
    client = client or PlatformClient()
    return client.push(assets, findings)
