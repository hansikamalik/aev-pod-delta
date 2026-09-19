"""
GCP Connector -- discovers Compute, Storage, IAM, and Cloud SQL
resources in a GCP project and normalizes them into the platform's
shared `Asset` shape.

Built against the `connector_sdk.Connector` contract frozen in Week 1
with the Integration squad. Follows the same pattern as the AWS and
Azure connectors: auth module -> credentials -> discover() -> normalize
-> ingest().
"""

from __future__ import annotations

from typing import Any, Iterable, Protocol

from connector_sdk import Asset, AssetType, Connector

from .auth import GCPAuthError, GCPServiceAccountAuth
from .client import FakeGCPAPIClient, GCPAPIClient, GCPClientProtocol


class PlatformClient(Protocol):
    """The platform's asset-ingestion client. A real implementation
    posts to the platform's asset service (`POST /assets/bulk`); the
    connector only depends on this narrow shape so it can be tested
    without the platform running.
    """

    def bulk_upsert(self, assets: list[Asset]) -> int: ...


class InMemoryPlatformClient:
    """Stand-in platform client used for local runs and tests. Mirrors
    the in-memory store in `connector_sdk.sample_connector.SampleConnector`.
    """

    def __init__(self, fail: bool = False) -> None:
        self._fail = fail
        self.pushed: list[Asset] = []

    def bulk_upsert(self, assets: list[Asset]) -> int:
        if self._fail:
            raise ConnectionError("simulated push failure")
        self.pushed.extend(assets)
        return len(assets)


class GCPConnector(Connector):
    """Discovers Compute instances, Storage buckets, IAM service
    accounts, and Cloud SQL instances from a single GCP project.
    """

    name = "gcp"

    def __init__(
        self,
        project_id: str,
        service_account_key_json: str | None = None,
        client: GCPClientProtocol | None = None,
        platform_client: PlatformClient | None = None,
    ) -> None:
        """
        Args:
            project_id: The GCP project to discover resources in.
            service_account_key_json: Raw JSON string of the service
                account key, as retrieved from the shared secrets vault.
                Not required if `client` is supplied directly (tests).
            client: Optional pre-built API client. If omitted, a real
                `GCPAPIClient` is constructed from the service account
                credentials on first use.
            platform_client: Where discovered assets are pushed. Defaults
                to an in-memory client suitable for local runs/tests; the
                real deployment wires in the platform's asset-service
                client.
        """
        self.project_id = project_id
        self._service_account_key_json = service_account_key_json
        self._client = client
        self._platform_client = platform_client or InMemoryPlatformClient()

    # -- internal helpers ---------------------------------------------

    def _auth(self) -> GCPServiceAccountAuth:
        if not self._service_account_key_json:
            raise GCPAuthError("service_account_key_json was not provided")
        return GCPServiceAccountAuth(self.project_id, self._service_account_key_json)

    def _get_client(self) -> GCPClientProtocol:
        if self._client is not None:
            return self._client
        credentials = self._auth().get_credentials()
        self._client = GCPAPIClient(self.project_id, credentials)
        return self._client

    @staticmethod
    def _normalize_instance(item: dict[str, Any]) -> Asset:
        return Asset(
            id=str(item["id"]),
            source="gcp",
            type=AssetType.COMPUTE,
            name=item["name"],
            raw=item,
            tags={"status": item.get("status", ""), "zone": item.get("zone", "").rsplit("/", 1)[-1]},
        )

    @staticmethod
    def _normalize_bucket(item: dict[str, Any]) -> Asset:
        return Asset(
            id=str(item["id"]),
            source="gcp",
            type=AssetType.STORAGE,
            name=item["name"],
            raw=item,
            tags={"location": item.get("location", ""), "storageClass": item.get("storageClass", "")},
        )

    @staticmethod
    def _normalize_service_account(item: dict[str, Any]) -> Asset:
        return Asset(
            id=str(item["uniqueId"]),
            source="gcp",
            type=AssetType.IDENTITY,
            name=item.get("email", item["uniqueId"]),
            raw=item,
            tags={"disabled": str(item.get("disabled", False))},
        )

    @staticmethod
    def _normalize_sql_instance(item: dict[str, Any]) -> Asset:
        # The shared Asset contract (frozen Week 1) doesn't define a
        # DATABASE AssetType, so Cloud SQL instances are normalized as
        # OTHER with a `resource_kind` tag -- same convention the AWS
        # connector would use for a resource type outside the 6 broad
        # categories.
        return Asset(
            id=item["name"],
            source="gcp",
            type=AssetType.OTHER,
            name=item["name"],
            raw=item,
            tags={
                "resource_kind": "cloudsql",
                "databaseVersion": item.get("databaseVersion", ""),
                "region": item.get("region", ""),
                "state": item.get("state", ""),
            },
        )

    # -- Connector interface --------------------------------------------

    def discover(self) -> Iterable[Asset]:
        client = self._get_client()
        assets: list[Asset] = []
        assets.extend(self._normalize_instance(i) for i in client.list_instances())
        assets.extend(self._normalize_bucket(b) for b in client.list_buckets())
        assets.extend(self._normalize_service_account(sa) for sa in client.list_service_accounts())
        assets.extend(self._normalize_sql_instance(s) for s in client.list_sql_instances())
        return assets

    def ingest(self, assets: Iterable[Asset]) -> int:
        return self._platform_client.bulk_upsert(list(assets))

    def check_health(self) -> bool:
        try:
            return self._get_client().ping()
        except GCPAuthError:
            return False

    def describe_config(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "GCP project ID to discover resources in"},
            },
            "required": ["project_id"],
        }

    def describe_credentials(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "service_account_key_json": {
                    "type": "string",
                    "secret": True,
                    "description": "Full JSON key for a read-only GCP service account",
                },
            },
            "required": ["service_account_key_json"],
        }
