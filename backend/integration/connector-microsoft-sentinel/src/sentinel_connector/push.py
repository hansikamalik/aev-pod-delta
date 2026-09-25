"""
Push normalized records to Beta's asset/exposure service.

Est: 0.5 day (per plan's per-connector standard pattern)

TODO(Harshal): Point BETA_ASSET_ENDPOINT at the real internal service
URL/hostname (likely resolved via service discovery / an internal
client rather than a hardcoded URL — this is a placeholder).
"""

from typing import List, Optional

import requests

from .base import Asset, SyncResult, utc_now_iso

BETA_ASSET_ENDPOINT = "https://internal.beta.platform/api/v1/assets/bulk"


class PushError(Exception):
    pass


class BetaPlatformPusher:
    def __init__(self, api_token: str, endpoint: str = BETA_ASSET_ENDPOINT, session: Optional[requests.Session] = None):
        self.api_token = api_token
        self.endpoint = endpoint
        self._session = session or requests.Session()

    def push(self, connector_name: str, assets: List[Asset], batch_size: int = 200) -> SyncResult:
        started_at = utc_now_iso()
        errors: List[str] = []
        pushed = 0

        for i in range(0, len(assets), batch_size):
            batch = assets[i : i + batch_size]
            payload = {"source": connector_name, "assets": [a.__dict__ for a in batch]}
            resp = self._session.post(
                self.endpoint,
                json=payload,
                headers={"Authorization": f"Bearer {self.api_token}"},
                timeout=30,
            )
            if resp.status_code not in (200, 201, 202):
                errors.append(
                    f"Batch {i // batch_size}: {resp.status_code} {resp.text[:200]}"
                )
            else:
                pushed += len(batch)

        return SyncResult(
            connector=connector_name,
            started_at=started_at,
            finished_at=utc_now_iso(),
            assets_count=pushed,
            findings_count=0,
            errors=errors,
        )
