"""
Push — sends normalized user/group assets to Pod Beta's asset service
(FR-INT: "Push to platform: Send to Beta's asset/exposure service"),
using the frozen v1.0 ingestion contract Pod Delta publishes
(POST /assets/ingest).

Active Directory has no separate alert/finding stream (unlike, say,
Microsoft Defender), so this connector only pushes assets.
"""

from __future__ import annotations

import httpx

from .exceptions import PushError
from .models import Asset


class PlatformPushClient:
    """Thin client for pushing discovered users/groups into the
    platform's asset ingestion API. `integration_id` is included on
    every payload so Beta can attribute records back to this
    integration."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        integration_id: str,
        asset_ingest_url: str,
        request_timeout_seconds: float = 30.0,
    ):
        self._http = http_client
        self._integration_id = integration_id
        self._asset_ingest_url = asset_ingest_url
        self._timeout = request_timeout_seconds

    async def push_asset(self, asset: Asset) -> None:
        body = {
            "integration_id": self._integration_id,
            "source": "active_directory",
            "external_id": asset.external_id,
            "name": asset.name,
            "type": asset.type,
            "attributes": asset.attributes,
            "tags": asset.tags,
        }
        try:
            response = await self._http.post(
                self._asset_ingest_url, json=body, timeout=self._timeout
            )
        except httpx.HTTPError as exc:
            raise PushError(f"Failed to push asset to {self._asset_ingest_url}: {exc}") from exc

        if response.status_code not in (200, 201, 202):
            raise PushError(
                f"Push of asset to {self._asset_ingest_url} returned "
                f"{response.status_code}: {response.text[:300]}"
            )
