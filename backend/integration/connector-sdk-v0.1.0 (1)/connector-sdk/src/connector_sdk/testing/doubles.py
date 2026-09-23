"""Test doubles: in-memory platform client and configurable fake connectors.

These exist so that every workstream can develop and test in parallel
without waiting for another member's module (the plan's "No Waiting"
principle).

  * :class:`InMemoryPlatformClient` — stands in for the platform asset
    service. Records upserts, supports upsert semantics, and can be told
    to reject specific asset IDs so partial-sync paths are testable.
  * :class:`FakeConnector` — a fully compliant connector whose behavior is
    configurable. Use it to test the scheduler, the distributed lock, and
    the Vault wiring with no real source system.
  * :class:`FailingConnector` — always fails, for negative-path tests.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from ..connector import Connector
from ..enums import AssetType
from ..exceptions import ConnectorError, IngestionError, SourceUnavailableError
from ..models import Asset, build_asset_id
from ..schemas import field, object_schema, secret_field


class InMemoryPlatformClient:
    """Stand-in for the platform asset service.

    Parameters
    ----------
    reject_ids:
        Asset IDs that the fake platform will refuse, producing a
        ``partial`` sync.
    fail_entirely:
        When True, every ``bulk_upsert`` raises :class:`IngestionError`.
    """

    def __init__(
        self,
        *,
        reject_ids: Iterable[str] = (),
        fail_entirely: bool = False,
    ) -> None:
        self.assets: dict[str, dict[str, Any]] = {}
        self.upsert_calls: list[int] = []
        self.reject_ids = set(reject_ids)
        self.fail_entirely = fail_entirely

    def bulk_upsert(self, assets: Sequence[Asset]) -> int:
        """Upsert assets by ID. Returns the number accepted."""
        if self.fail_entirely:
            raise IngestionError(
                "Platform asset service unavailable",
                operation="ingest",
                status_code=503,
                retryable=True,
            )
        accepted = 0
        for asset in assets:
            if asset.id in self.reject_ids:
                continue
            # Upsert semantics: same ID overwrites rather than duplicating.
            self.assets[asset.id] = asset.to_dict()
            accepted += 1
        self.upsert_calls.append(accepted)
        return accepted

    @property
    def count(self) -> int:
        return len(self.assets)

    def reset(self) -> None:
        self.assets.clear()
        self.upsert_calls.clear()


def sample_resources(count: int = 3, prefix: str = "vm") -> list[dict[str, Any]]:
    """Deterministic fake source-system payloads."""
    return [
        {
            "id": f"{prefix}-{index:04d}",
            "name": f"{prefix}-host-{index:02d}",
            "location": "eastus",
            "properties": {"vmSize": "Standard_D2s_v3", "provisioningState": "Succeeded"},
            "tags": {"env": "test", "owner": "integration-squad"},
        }
        for index in range(1, count + 1)
    ]


class FakeConnector(Connector):
    """A fully contract-compliant connector backed by in-memory data.

    Use as the "dummy connector" referenced throughout the sprint plan --
    for contract-test verification, scheduler and distributed-lock testing,
    and the Week 1 demo.

    Examples
    --------
    Healthy three-asset sync::

        connector = FakeConnector()
        result = connector.sync_blocking()
        assert result.status == "success"

    Partial sync (platform rejects one asset)::

        platform = InMemoryPlatformClient(reject_ids={"vm-0002"})
        connector = FakeConnector(platform=platform)
        assert connector.sync_blocking().status == "partial"

    Source outage::

        connector = FakeConnector(healthy=False, raise_on_discover=True)
        assert connector.sync_blocking().status == "failed"
    """

    name = "fake"

    def __init__(
        self,
        *,
        resources: Sequence[Mapping[str, Any]] | None = None,
        platform: InMemoryPlatformClient | None = None,
        asset_type: AssetType = AssetType.COMPUTE,
        healthy: bool = True,
        raise_on_discover: bool = False,
        config: Mapping[str, Any] | None = None,
        credentials: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            config=config if config is not None else {"region": "eastus"},
            credentials=credentials if credentials is not None else {"api_key": "fake-secret"},
        )
        self._resources = list(resources if resources is not None else sample_resources())
        self.platform = platform or InMemoryPlatformClient()
        self._asset_type = asset_type
        self._healthy = healthy
        self._raise_on_discover = raise_on_discover
        self.discover_call_count = 0

    # -- interface -----------------------------------------------------

    def discover(self) -> Iterable[Asset]:
        self.discover_call_count += 1
        if self._raise_on_discover:
            raise SourceUnavailableError(
                "Fake source is unreachable",
                operation="discover",
                source=self.name,
                status_code=503,
            )
        for resource in self._resources:
            yield Asset(
                id=resource["id"],
                source=self.name,
                type=self._asset_type,
                name=resource["name"],
                raw=resource,
                tags=dict(resource.get("tags", {})),
            )

    def ingest(self, assets: Iterable[Asset]) -> int:
        assets = list(assets)
        if not assets:
            return 0
        return self.platform.bulk_upsert(assets)

    def check_health(self) -> bool:
        return bool(self._healthy)

    def describe_config(self) -> dict:
        return object_schema(
            {"region": field("string", description="Fake source region")},
            required=["region"],
        )

    def describe_credentials(self) -> dict:
        return object_schema(
            {"api_key": secret_field("Fake source API key")},
            required=["api_key"],
        )


class FailingConnector(FakeConnector):
    """Always-failing connector for negative-path and alerting tests."""

    name = "failing"

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("healthy", False)
        kwargs.setdefault("raise_on_discover", True)
        super().__init__(**kwargs)


__all__ = [
    "InMemoryPlatformClient",
    "FakeConnector",
    "FailingConnector",
    "sample_resources",
    "build_asset_id",
    "ConnectorError",
]
