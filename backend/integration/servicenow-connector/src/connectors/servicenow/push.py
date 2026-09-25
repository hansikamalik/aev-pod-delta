"""Push stage: send normalized Assets/Findings to the Beta platform services."""

from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional

import requests


class PushError(Exception):
    """Raised when a push batch fails permanently."""


class PlatformPusher:
    """Batches upserts to the asset and exposure (finding) services."""

    DEFAULT_BATCH = 500

    def __init__(
        self,
        asset_url: str,
        exposure_url: str,
        token: Optional[str] = None,
        timeout: int = 30,
        batch_size: int = DEFAULT_BATCH,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.asset_url = asset_url
        self.exposure_url = exposure_url
        self.token = token or os.environ.get("AEV_PLATFORM_TOKEN", "")
        self.timeout = timeout
        self.batch_size = batch_size
        self.session = session or requests.Session()

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    # ------------------------------------------------------------------ #
    def push_assets(self, assets: Iterable[Dict[str, Any]]) -> Dict[str, int]:
        return self._push(self.asset_url, assets)

    def push_findings(self, findings: Iterable[Dict[str, Any]]) -> Dict[str, int]:
        return self._push(self.exposure_url, findings)

    # ------------------------------------------------------------------ #
    def _push(self, url: str, records: Iterable[Dict[str, Any]]) -> Dict[str, int]:
        stats = {"sent": 0, "accepted": 0, "failed": 0}
        batch: List[Dict[str, Any]] = []

        def flush() -> None:
            if not batch:
                return
            resp = self.session.post(
                url, headers=self._headers(),
                json={"records": list(batch)}, timeout=self.timeout,
            )
            stats["sent"] += len(batch)
            if resp.status_code in (200, 201, 202):
                stats["accepted"] += len(batch)
            else:
                stats["failed"] += len(batch)
                raise PushError(f"push to {url} failed: {resp.status_code} {resp.text[:300]}")
            batch.clear()

        for rec in records:
            batch.append(rec)
            if len(batch) >= self.batch_size:
                flush()
        flush()
        return stats
