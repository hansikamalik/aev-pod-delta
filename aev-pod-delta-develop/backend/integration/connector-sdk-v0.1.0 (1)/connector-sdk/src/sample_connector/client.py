"""Fake source-system client for the reference connector.

Demonstrates the Section 24 separation: all API communication lives here,
never inside the connector. Also demonstrates cursor pagination
(Section 21) — the connector must walk every page.
"""

from __future__ import annotations

from typing import Any, Iterator


def _fixture_resources(count: int = 7) -> list[dict[str, Any]]:
    kinds = ["server", "bucket", "user", "vnet", "widget"]
    return [
        {
            "id": f"sample-{index:04d}",
            "name": f"resource-{index:02d}",
            "kind": kinds[index % len(kinds)],
            "region": "eastus",
            "tags": {"env": "reference"},
        }
        for index in range(count)
    ]


class SampleSourceClient:
    """Stand-in for a real paginated source API."""

    def __init__(
        self,
        region: str = "eastus",
        api_key: str | None = None,
        *,
        resources: list[dict[str, Any]] | None = None,
        reachable: bool = True,
    ) -> None:
        self.region = region
        # Held only to demonstrate credential flow; never logged or
        # placed into an Asset's raw payload.
        self._api_key = api_key
        self._resources = resources if resources is not None else _fixture_resources()
        self._reachable = reachable
        self.page_requests = 0

    def ping(self) -> bool:
        """Cheap reachability + credential check."""
        return bool(self._reachable and self._api_key)

    def iter_resources(self, page_size: int = 50) -> Iterator[dict[str, Any]]:
        """Yield every resource, walking all pages via a cursor."""
        if not self._reachable:
            raise ConnectionError("sample source unreachable")

        cursor = 0
        while True:
            self.page_requests += 1
            page = self._resources[cursor : cursor + page_size]
            for resource in page:
                yield dict(resource)
            cursor += page_size
            if cursor >= len(self._resources):
                break


__all__ = ["SampleSourceClient", "SampleSourceClient"]
