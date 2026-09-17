"""
Dummy connector — reference implementation of the Connector SDK contract
(contract_v2). Used by contract tests, by Abhiram's infra work, and by the
integration suite as the always-available connector.

Config/credential injection is NOT part of the abstract contract (§18/§19
define only describe_*); `_apply_config`/`_apply_credentials` here are the
conventional way the runtime hands them over.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from qa.contracts import (
    Asset,
    AuthError,
    ConfigError,
    Connector,
    SyncResult,
)


class DummyConnector(Connector):
    """Fully contract-conformant dummy. Inject failures for negative tests."""

    def __init__(
        self,
        name: str = "dummy",
        fail_health: bool = False,
        fail_ingest: bool = False,
        pages: Optional[List[List[Dict[str, Any]]]] = None,
    ) -> None:
        self._name = name
        self._fail_health = fail_health
        self._fail_ingest = fail_ingest
        self._pages = pages or [[
            {"resourceId": "res-alpha", "resourceName": "alpha", "kind": "thing"},
            {"resourceId": "res-beta", "resourceName": "beta", "kind": "thing"},
        ]]
        self._config: Dict[str, Any] = {}
        self._creds: Dict[str, str] = {}
        self._platform: List[Asset] = []          # what ingest() "pushed"
        self._page_cursor = 0

    # -- contract surface (§3) ----------------------------------------------
    @property
    def name(self) -> str:
        return self._name

    def discover(self) -> Iterable[Asset]:
        """Read-only, paginated (§21): walks _pages, yields normalized Assets."""
        now = datetime.now(timezone.utc).isoformat()
        while self._page_cursor < len(self._pages):
            for item in self._pages[self._page_cursor]:
                yield Asset(
                    id=item["resourceId"],                 # §6: stable source id
                    source=self.name,                      # §7
                    type="other",                          # §8 normalized type
                    name=item.get("resourceName", item["resourceId"]),
                    raw=item,                              # §9
                    discoveredAt=now,
                )
            self._page_cursor += 1
        self._page_cursor = 0  # restartable — discover() is repeatable

    def ingest(self, assets: Iterable[Asset]) -> int:
        """Platform push (§11/§12): upsert by asset id; count only pushed."""
        pushed = 0
        for asset in assets:
            if self._fail_ingest:
                continue  # platform rejected — must NOT be counted (§11)
            upsert = {a.id: a for a in self._platform}  # §12: no duplicates
            upsert[asset.id] = asset
            self._platform = list(upsert.values())
            pushed += 1
        return pushed

    def check_health(self) -> bool:
        """§17: never raises; False on unhealthy backend."""
        return not self._fail_health

    def describe_config(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "endpoint": {"type": "string"},
                "poll_interval": {"type": "integer"},
            },
            "required": ["endpoint"],
        }

    def describe_credentials(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "api_key": {"type": "string", "secret": True},
            },
            "required": ["api_key"],
        }

    # -- runtime injection (not part of the abstract contract) --------------
    def _apply_config(self, config: Dict[str, Any]) -> None:
        schema = self.describe_config()
        required = schema.get("required", [])
        missing = [k for k in required if k not in config]
        if missing:
            raise ConfigError(f"missing required config: {missing}")
        self._config = dict(config)

    def _apply_credentials(self, credentials: Dict[str, str]) -> None:
        schema = self.describe_credentials()
        required = schema.get("required", [])
        missing = [k for k in required if k not in credentials]
        if missing:
            raise AuthError(f"missing required credentials: {missing}")
        self._creds = dict(credentials)

    # -- test helpers ---------------------------------------------------------
    @property
    def platform(self) -> List[Asset]:
        return list(self._platform)
