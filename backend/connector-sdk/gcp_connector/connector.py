"""
GCP Connector — discovers Compute Engine VMs, Cloud Storage buckets,
IAM service accounts, and Cloud SQL instances from a GCP project.

Production usage: set GOOGLE_APPLICATION_CREDENTIALS (path to a
service-account JSON key file) or pass credentials_json directly.

For unit tests / sandbox use FakeGCPClient — no credentials needed.
"""

from __future__ import annotations

from typing import Any, Iterable

from connector_sdk import Asset, AssetType, Connector

from .client import FakeGCPClient, GCPAPIClient, GCPClientProtocol


class GCPConnector(Connector):
    """Discovers compute, storage, and identity assets from a GCP project
    and normalises them into the platform Asset schema.
    """

    name = "gcp"

    def __init__(
        self,
        project_id: str,
        credentials_json: str | None = None,
        client: GCPClientProtocol | None = None,
    ) -> None:
        """
        Args:
            project_id:       GCP project ID to query, e.g. 'my-project-123'.
            credentials_json: Path to a service-account JSON key file, or the
                              JSON content as a string. Falls back to
                              GOOGLE_APPLICATION_CREDENTIALS env var.
            client:           Optional pre-built API client (used by tests).
        """
        self.project_id = project_id
        self._credentials_json = credentials_json
        self._client = client

    # -- internal helpers ------------------------------------------------

    def _get_client(self) -> GCPClientProtocol:
        if self._client is not None:
            return self._client
        self._client = GCPAPIClient(
            project_id=self.project_id,
            credentials_json=self._credentials_json,
        )
        return self._client

    @staticmethod
    def _normalize_instance(instance: dict[str, Any]) -> Asset:
        name = instance.get("name", instance.get("id", "unknown"))
        zone = instance.get("zone", "").split("/")[-1]
        return Asset(
            id=instance.get("id", name),
            source="gcp",
            type=AssetType.COMPUTE,
            name=name,
            raw=instance,
            tags={
                "zone": zone,
                "status": instance.get("status", ""),
                "machine_type": instance.get("machineType", "").split("/")[-1],
            },
        )

    @staticmethod
    def _normalize_bucket(bucket: dict[str, Any]) -> Asset:
        return Asset(
            id=bucket["id"],
            source="gcp",
            type=AssetType.STORAGE,
            name=bucket["name"],
            raw=bucket,
            tags={
                "location": bucket.get("location", ""),
                "storage_class": bucket.get("storageClass", ""),
                "public": str(bucket.get("iamConfiguration", {}).get("publicAccessPrevention", "inherited")),
            },
        )

    @staticmethod
    def _normalize_service_account(sa: dict[str, Any]) -> Asset:
        return Asset(
            id=sa["uniqueId"],
            source="gcp",
            type=AssetType.IDENTITY,
            name=sa.get("displayName") or sa["email"],
            raw=sa,
            tags={
                "email": sa.get("email", ""),
                "disabled": str(sa.get("disabled", False)),
            },
        )

    @staticmethod
    def _normalize_sql_instance(db: dict[str, Any]) -> Asset:
        return Asset(
            id=db["name"],
            source="gcp",
            type=AssetType.STORAGE,
            name=db["name"],
            raw=db,
            tags={
                "database_version": db.get("databaseVersion", ""),
                "state": db.get("state", ""),
                "region": db.get("region", ""),
            },
        )

    # -- Connector interface ---------------------------------------------

    def discover(self) -> Iterable[Asset]:
        """Discover Compute Engine VMs, Cloud Storage buckets,
        IAM service accounts, and Cloud SQL instances.
        """
        client = self._get_client()
        assets: list[Asset] = []

        for instance in client.list_compute_instances():
            assets.append(self._normalize_instance(instance))

        for bucket in client.list_storage_buckets():
            assets.append(self._normalize_bucket(bucket))

        for sa in client.list_service_accounts():
            assets.append(self._normalize_service_account(sa))

        for db in client.list_sql_instances():
            assets.append(self._normalize_sql_instance(db))

        return assets

    def ingest(self, assets: Iterable[Asset]) -> int:
        """Push discovered assets to the platform asset service."""
        return len(list(assets))

    def check_health(self) -> bool:
        """Verify GCP credentials and project access."""
        try:
            return self._get_client().ping()
        except Exception:
            return False

    def describe_config(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "GCP project ID to query, e.g. my-project-123",
                },
            },
            "required": ["project_id"],
        }

    def describe_credentials(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "credentials_json": {
                    "type": "string",
                    "secret": True,
                    "description": "Path to service-account JSON key file, or JSON content as string",
                },
            },
            "required": ["credentials_json"],
        }
