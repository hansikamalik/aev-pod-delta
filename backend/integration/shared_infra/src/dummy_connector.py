"""
Dummy Connector
Used by Abhiram to develop/test Shared Infrastructure (vault, scheduler,
lock) without waiting on the real Azure or Splunk connectors, and by
Harshal's Connector Foundation to validate the shared contract.

Implements the same minimal contract shape as the real connectors:
  configure(credentials), health(), sync(payload)
"""

from __future__ import annotations

from typing import Optional


class DummyConnector:
    def __init__(self):
        self.configured = False
        self.sync_count = 0
        self.last_payload = None

    def configure(self, credentials: Optional[str]) -> None:
        if not credentials:
            raise ValueError("DummyConnector requires a non-empty credential")
        self.configured = True

    def health(self) -> dict:
        return {"status": "healthy" if self.configured else "unconfigured", "reachable": self.configured}

    def sync(self, payload=None) -> dict:
        self.sync_count += 1
        self.last_payload = payload
        return {"status": "ok", "run": self.sync_count}
