"""
Ingestion — pulls alerts from Microsoft Defender for Endpoint, filtered
by lastUpdateTime so incremental syncs only fetch what changed
(FR-INT-028 Incremental, owned by the sync engine layer that calls this
connector — this module just accepts a `since` cursor).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import AsyncIterator

import httpx

from .auth import DefenderAuthClient
from .config import DefenderConfig
from .exceptions import DefenderAPIError


async def iter_alerts(
    config: DefenderConfig,
    auth: DefenderAuthClient,
    http_client: httpx.AsyncClient,
    since: datetime | None = None,
) -> AsyncIterator[dict]:
    """Yield raw alert records from the Defender /api/alerts endpoint,
    updated at or after `since` (defaults to config.alert_lookback_hours
    before now on first sync)."""

    if since is None:
        since = datetime.now(timezone.utc) - timedelta(hours=config.alert_lookback_hours)

    url = f"{config.api_base_url}api/alerts"
    params = {"$filter": f"lastUpdateTime ge {since.strftime('%Y-%m-%dT%H:%M:%SZ')}"}

    while url:
        headers = await auth.auth_headers()
        try:
            response = await http_client.get(
                url, headers=headers, params=params, timeout=config.request_timeout_seconds
            )
        except httpx.HTTPError as exc:
            raise DefenderAPIError(f"Alerts request failed: {exc}") from exc

        if response.status_code == 401:
            headers = {**headers, "Authorization": f"Bearer {await auth.get_token(force_refresh=True)}"}
            response = await http_client.get(
                url, headers=headers, params=params, timeout=config.request_timeout_seconds
            )

        if response.status_code != 200:
            raise DefenderAPIError(
                f"Alerts request returned {response.status_code}: {response.text[:300]}",
                status_code=response.status_code,
            )

        payload = response.json()
        for alert in payload.get("value", []):
            yield alert

        url = payload.get("@odata.nextLink")
        params = None
