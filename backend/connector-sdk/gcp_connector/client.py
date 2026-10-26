"""
Thin wrapper around GCP APIs this connector needs.

GCPAPIClient  — production implementation using google-cloud-* SDKs (lazy import).
FakeGCPClient — canned data for unit tests and sandbox — no credentials needed.
"""

from __future__ import annotations

from typing import Any, Protocol


class GCPClientProtocol(Protocol):
    def list_compute_instances(self) -> list[dict[str, Any]]: ...
    def list_storage_buckets(self) -> list[dict[str, Any]]: ...
    def list_service_accounts(self) -> list[dict[str, Any]]: ...
    def list_sql_instances(self) -> list[dict[str, Any]]: ...
    def ping(self) -> bool: ...


class GCPAPIClient:
    """Production client backed by google-cloud-* SDKs.

    Dependencies are imported lazily so this module stays importable in
    unit tests without the GCP SDK installed.
    """

    def __init__(self, project_id: str, credentials_json: str | None = None) -> None:
        self.project_id = project_id
        self._credentials_json = credentials_json

    def _credentials(self):
        if not self._credentials_json:
            return None  # fall through to ADC (GOOGLE_APPLICATION_CREDENTIALS)
        import json
        import os

        from google.oauth2 import service_account  # type: ignore

        if os.path.isfile(self._credentials_json):
            return service_account.Credentials.from_service_account_file(self._credentials_json)
        return service_account.Credentials.from_service_account_info(json.loads(self._credentials_json))

    def list_compute_instances(self) -> list[dict[str, Any]]:
        from google.cloud import compute_v1  # type: ignore

        creds = self._credentials()
        client = compute_v1.InstancesClient(credentials=creds)
        instances: list[dict[str, Any]] = []
        for zone_instances in client.aggregated_list(project=self.project_id):
            _zone, scoped = zone_instances
            for inst in scoped.instances or []:
                instances.append(type(inst).to_dict(inst))
        return instances

    def list_storage_buckets(self) -> list[dict[str, Any]]:
        from google.cloud import storage  # type: ignore

        creds = self._credentials()
        client = storage.Client(project=self.project_id, credentials=creds)
        return [b._properties for b in client.list_buckets()]

    def list_service_accounts(self) -> list[dict[str, Any]]:
        import googleapiclient.discovery  # type: ignore

        creds = self._credentials()
        iam = googleapiclient.discovery.build("iam", "v1", credentials=creds)
        resp = iam.projects().serviceAccounts().list(name=f"projects/{self.project_id}").execute()
        return resp.get("accounts", [])

    def list_sql_instances(self) -> list[dict[str, Any]]:
        import googleapiclient.discovery  # type: ignore

        creds = self._credentials()
        sqladmin = googleapiclient.discovery.build("sqladmin", "v1", credentials=creds)
        resp = sqladmin.instances().list(project=self.project_id).execute()
        return resp.get("items", [])

    def ping(self) -> bool:
        try:
            import googleapiclient.discovery  # type: ignore

            creds = self._credentials()
            crm = googleapiclient.discovery.build("cloudresourcemanager", "v1", credentials=creds)
            crm.projects().get(projectId=self.project_id).execute()
            return True
        except Exception:
            return False


class FakeGCPClient:
    """Canned data for unit tests and sandbox — no GCP credentials needed."""

    def __init__(self, fail_ping: bool = False) -> None:
        self._fail_ping = fail_ping

    def list_compute_instances(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "1234567890123456789",
                "name": "api-server-prod-1",
                "status": "RUNNING",
                "zone": "projects/my-project/zones/us-central1-a",
                "machineType": "projects/my-project/machineTypes/n2-standard-4",
            },
            {
                "id": "9876543210987654321",
                "name": "batch-worker-1",
                "status": "RUNNING",
                "zone": "projects/my-project/zones/us-central1-b",
                "machineType": "projects/my-project/machineTypes/n2-standard-2",
            },
        ]

    def list_storage_buckets(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "aev-gcs-uploads-prod",
                "name": "aev-gcs-uploads-prod",
                "location": "US",
                "storageClass": "STANDARD",
                "iamConfiguration": {"publicAccessPrevention": "enforced"},
            },
            {
                "id": "aev-gcs-audit-logs",
                "name": "aev-gcs-audit-logs",
                "location": "US",
                "storageClass": "COLDLINE",
                "iamConfiguration": {"publicAccessPrevention": "inherited"},
            },
        ]

    def list_service_accounts(self) -> list[dict[str, Any]]:
        return [
            {
                "uniqueId": "112233445566778899001",
                "email": "aev-backend@my-project.iam.gserviceaccount.com",
                "displayName": "AEV Backend Service Account",
                "disabled": False,
            },
            {
                "uniqueId": "998877665544332211002",
                "email": "legacy-data-pipeline@my-project.iam.gserviceaccount.com",
                "displayName": "Legacy Data Pipeline",
                "disabled": True,
            },
        ]

    def list_sql_instances(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "aev-postgres-primary",
                "databaseVersion": "POSTGRES_15",
                "state": "RUNNABLE",
                "region": "us-central1",
            },
        ]

    def ping(self) -> bool:
        return not self._fail_ping
