from __future__ import annotations

from typing import Any, Iterable

import httpx

from connector_sdk import Asset, AssetType, Connector


class ReferenceConnector(Connector):
    """Reference HTTP connector used by the Python Sandbox."""

    name = "reference"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 5.0,
        extra_params: dict[str, str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.extra_params = extra_params or {}
        self._pushed_assets: list[Asset] = []

    def discover(self) -> Iterable[Asset]:
        response = httpx.get(
            f"{self.base_url}/api/assets",
            headers={"Authorization": f"Bearer {self.api_key}"},
            params=self.extra_params,
            timeout=self.timeout,
        )

        response.raise_for_status()

        data = response.json()

        return [
            Asset(
                id=item["id"],
                source=self.name,
                type=AssetType(item.get("type", "other")),
                name=item["name"],
                raw=item,
            )
            for item in data.get("assets", [])
        ]

    def ingest(self, assets: Iterable[Asset]) -> int:
        assets = list(assets)
        self._pushed_assets.extend(assets)
        return len(assets)

    def check_health(self) -> bool:
        try:
            response = httpx.get(
                f"{self.base_url}/health",
                timeout=self.timeout,
            )
            return response.is_success
        except httpx.HTTPError:
            return False

    def describe_config(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "base_url": {
                    "type": "string",
                    "description": "Base URL of the vendor API",
                },
            },
            "required": ["base_url"],
        }

    def describe_credentials(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "api_key": {
                    "type": "string",
                    "secret": True,
                },
            },
            "required": ["api_key"],
        }