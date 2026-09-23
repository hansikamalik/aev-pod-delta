"""
Push normalized assets to the platform's asset/exposure ingestion service.

TODO: Swap for the shared platform client once available (same swap as the
SentinelOne connector's push module — this file wasn't available to model
against, so this is a standalone implementation against the documented
ingestion contract: POST /assets/ingest).
"""

import logging
from dataclasses import asdict
from typing import List

import requests

from .base import Asset, SyncResult, utc_now_iso

logger = logging.getLogger("google_workspace_connector.push")

_INGEST_PATH = "/assets/ingest"
_DEFAULT_TIMEOUT_SECONDS = 30


class BetaPlatformPusher:
    def __init__(self, api_token: str, base_url: str = "https://platform.internal"):
        self._api_token = api_token
        self._base_url = base_url.rstrip("/")

    def push(self, connector_name: str, assets: List[Asset]) -> SyncResult:
        started_at = utc_now_iso()
        errors: List[str] = []

        try:
            response = requests.post(
                f"{self._base_url}{_INGEST_PATH}",
                json={
                    "connector": connector_name,
                    "assets": [asdict(asset) for asset in assets],
                },
                headers={"Authorization": f"Bearer {self._api_token}"},
                timeout=_DEFAULT_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            errors.append(str(exc))
            logger.error("google_workspace_connector.push.error=%s", exc)

        return SyncResult(
            connector=connector_name,
            started_at=started_at,
            finished_at=utc_now_iso(),
            assets_count=len(assets),
            findings_count=0,  # set by the caller once findings are known
            errors=errors,
        )
