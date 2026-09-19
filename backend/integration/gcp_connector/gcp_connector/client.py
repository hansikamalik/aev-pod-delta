"""
Thin wrapper around the GCP APIs the connector discovers assets from:

  - Compute Engine   (VM instances)
  - Cloud Storage    (buckets)
  - IAM              (service accounts)
  - Cloud SQL        (database instances)

`GCPAPIClient` is the production implementation, built on
`google-api-python-client`. `FakeGCPAPIClient` returns canned data with
the same shape and is what the connector is exercised against in this
sandbox (no network access) and in unit tests -- same pattern as
`connector_sdk.sample_connector`, and the same "sandbox/mock account"
approach called out for the AWS connector's integration test.

Swapping `GCPAPIClient` in for `FakeGCPAPIClient` at construction time
is the only change needed to point the connector at a real project.
"""

from __future__ import annotations

from typing import Any, Protocol


class GCPClientProtocol(Protocol):
    """Shape both the real and fake clients implement."""

    def list_instances(self) -> list[dict[str, Any]]: ...

    def list_buckets(self) -> list[dict[str, Any]]: ...

    def list_service_accounts(self) -> list[dict[str, Any]]: ...

    def list_sql_instances(self) -> list[dict[str, Any]]: ...

    def ping(self) -> bool: ...


class GCPAPIClient:
    """Production client, backed by `google-api-python-client`.

    Built lazily: `googleapiclient` is imported inside each method so the
    connector module stays importable without the dependency installed
    (e.g. for schema inspection or unit tests using the fake client).
    """

    def __init__(self, project_id: str, credentials) -> None:
        self.project_id = project_id
        self._credentials = credentials

    def _build(self, service: str, version: str):
        from googleapiclient.discovery import build  # type: ignore

        return build(service, version, credentials=self._credentials, cache_discovery=False)

    def list_instances(self) -> list[dict[str, Any]]:
        compute = self._build("compute", "v1")
        instances: list[dict[str, Any]] = []
        request = compute.instances().aggregatedList(project=self.project_id)
        while request is not None:
            response = request.execute()
            for _zone, scoped_list in response.get("items", {}).items():
                instances.extend(scoped_list.get("instances", []))
            request = compute.instances().aggregatedList_next(
                previous_request=request, previous_response=response
            )
        return instances

    def list_buckets(self) -> list[dict[str, Any]]:
        storage = self._build("storage", "v1")
        buckets: list[dict[str, Any]] = []
        request = storage.buckets().list(project=self.project_id)
        while request is not None:
            response = request.execute()
            buckets.extend(response.get("items", []))
            request = storage.buckets().list_next(request, response)
        return buckets

    def list_service_accounts(self) -> list[dict[str, Any]]:
        iam = self._build("iam", "v1")
        accounts: list[dict[str, Any]] = []
        request = iam.projects().serviceAccounts().list(name=f"projects/{self.project_id}")
        while request is not None:
            response = request.execute()
            accounts.extend(response.get("accounts", []))
            request = iam.projects().serviceAccounts().list_next(request, response)
        return accounts

    def list_sql_instances(self) -> list[dict[str, Any]]:
        sqladmin = self._build("sqladmin", "v1beta4")
        instances: list[dict[str, Any]] = []
        request = sqladmin.instances().list(project=self.project_id)
        while request is not None:
            response = request.execute()
            instances.extend(response.get("items", []))
            request = sqladmin.instances().list_next(request, response)
        return instances

    def ping(self) -> bool:
        try:
            self._build("compute", "v1").zones().list(project=self.project_id, maxResults=1).execute()
            return True
        except Exception:
            return False


class FakeGCPAPIClient:
    """Canned data standing in for a real GCP project. Used for unit
    tests and for integration testing in this sandbox, which has no
    network access -- mirrors the AWS/Azure connectors' sandbox-account
    testing approach.
    """

    def __init__(self, fail_ping: bool = False) -> None:
        self._fail_ping = fail_ping

    def list_instances(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "1234567890",
                "name": "app-server-1",
                "zone": "projects/demo-project/zones/us-central1-a",
                "status": "RUNNING",
                "machineType": "n2-standard-4",
            },
            {
                "id": "1234567891",
                "name": "worker-node-2",
                "zone": "projects/demo-project/zones/us-central1-b",
                "status": "RUNNING",
                "machineType": "n2-standard-2",
            },
        ]

    def list_buckets(self) -> list[dict[str, Any]]:
        return [
            {"id": "demo-app-uploads", "name": "demo-app-uploads", "location": "US", "storageClass": "STANDARD"},
        ]

    def list_service_accounts(self) -> list[dict[str, Any]]:
        return [
            {
                "uniqueId": "111122223333",
                "email": "copilot-runner@demo-project.iam.gserviceaccount.com",
                "displayName": "Copilot Runner",
                "disabled": False,
            },
        ]

    def list_sql_instances(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "prod-postgres",
                "databaseVersion": "POSTGRES_15",
                "region": "us-central1",
                "state": "RUNNABLE",
            },
        ]

    def ping(self) -> bool:
        return not self._fail_ping
