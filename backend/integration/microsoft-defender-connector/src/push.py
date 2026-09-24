"""
Push — sends normalized assets and findings to Pod Beta's asset/exposure
services (FR-INT: "Push to platform: Send to Beta's asset/exposure
service"), using the frozen v1.0 ingestion contract Pod Delta publishes
(POST /assets/ingest).
"""

from __future__ import annotations

import httpx

from .exceptions import PushError
from .models import Asset, Finding


class PlatformPushClient:
    """Thin client for pushing discovered assets and findings into the
    platform's ingestion APIs. `integration_id` is included on every
    payload so Beta can attribute records back to this integration."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        integration_id: str,
        asset_ingest_url: str,
        exposure_ingest_url: str,
        request_timeout_seconds: float = 30.0,
    ):
        self._http = http_client
        self._integration_id = integration_id
        self._asset_ingest_url = asset_ingest_url
        self._exposure_ingest_url = exposure_ingest_url
        self._timeout = request_timeout_seconds

    async def push_asset(self, asset: Asset) -> None:
        body = {
            "integration_id": self._integration_id,
            "source": "microsoft_defender",
            "external_id": asset.external_id,
            "name": asset.name,
            "type": asset.type,
            "attributes": asset.attributes,
            "tags": asset.tags,
        }
        await self._post(self._asset_ingest_url, body, what="asset")

    async def push_finding(self, finding: Finding) -> None:
        await self.push_finding_dict(finding.to_dict())

    async def push_finding_dict(self, finding: dict) -> None:
        """Push an already-normalized finding dict, as yielded by
        Connector.ingest(). Used by sync(), which works with ingest()'s
        AsyncIterator[dict] output rather than Finding objects."""
        body = {
            "integration_id": self._integration_id,
            "source": "microsoft_defender",
            **finding,
        }
        await self._post(self._exposure_ingest_url, body, what="finding")

    async def _post(self, url: str, body: dict, *, what: str) -> None:
        try:
            response = await self._http.post(url, json=body, timeout=self._timeout)
        except httpx.HTTPError as exc:
            raise PushError(f"Failed to push {what} to {url}: {exc}") from exc

        if response.status_code not in (200, 201, 202):
            raise PushError(
                f"Push of {what} to {url} returned {response.status_code}: {response.text[:300]}"
            )
