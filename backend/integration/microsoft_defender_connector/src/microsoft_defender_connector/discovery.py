"""
Discovery — pulls machines (devices) from Microsoft Defender for
Endpoint. Paginated via @odata.nextLink, as the /api/machines endpoint
returns.
"""

from __future__ import annotations

from typing import AsyncIterator

import httpx

from .auth import DefenderAuthClient
from .config import DefenderConfig
from .exceptions import DefenderAPIError


async def iter_machines(
    config: DefenderConfig,
    auth: DefenderAuthClient,
    http_client: httpx.AsyncClient,
) -> AsyncIterator[dict]:
    """Yield raw machine records from the Defender /api/machines endpoint,
    following pagination until exhausted."""

    url = f"{config.api_base_url}api/machines"
    params = {"$top": config.machine_page_size}

    while url:
        headers = await auth.auth_headers()
        try:
            response = await http_client.get(
                url, headers=headers, params=params, timeout=config.request_timeout_seconds
            )
        except httpx.HTTPError as exc:
            raise DefenderAPIError(f"Machines request failed: {exc}") from exc

        if response.status_code == 401:
            # Token may have been revoked server-side; force a fresh one and retry once.
            headers = {**headers, "Authorization": f"Bearer {await auth.get_token(force_refresh=True)}"}
            response = await http_client.get(
                url, headers=headers, params=params, timeout=config.request_timeout_seconds
            )

        if response.status_code != 200:
            raise DefenderAPIError(
                f"Machines request returned {response.status_code}: {response.text[:300]}",
                status_code=response.status_code,
            )

        payload = response.json()
        for machine in payload.get("value", []):
            yield machine

        url = payload.get("@odata.nextLink")
        params = None  # nextLink already carries query params
