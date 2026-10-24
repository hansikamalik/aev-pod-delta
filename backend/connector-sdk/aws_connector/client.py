"""
Thin wrapper around the AWS APIs this connector needs.

AWSAPIClient  — production implementation using boto3 (lazy import).
FakeAWSClient — canned data with the same shape; used in unit tests
                and the sandbox so no real AWS credentials are needed.
"""

from __future__ import annotations

from typing import Any, Protocol


class AWSClientProtocol(Protocol):
    def list_ec2_instances(self) -> list[dict[str, Any]]: ...
    def list_s3_buckets(self) -> list[dict[str, Any]]: ...
    def list_iam_roles(self) -> list[dict[str, Any]]: ...
    def list_rds_instances(self) -> list[dict[str, Any]]: ...
    def list_lambda_functions(self) -> list[dict[str, Any]]: ...
    def ping(self) -> bool: ...


class AWSAPIClient:
    """Production client backed by boto3.

    boto3 is imported lazily so this module stays importable in unit
    tests without the AWS SDK installed.
    """

    def __init__(
        self,
        region: str = "us-east-1",
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
    ) -> None:
        self.region = region
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key

    def _session(self):
        import boto3  # type: ignore

        kwargs: dict[str, Any] = {"region_name": self.region}
        if self._access_key_id:
            kwargs["aws_access_key_id"] = self._access_key_id
        if self._secret_access_key:
            kwargs["aws_secret_access_key"] = self._secret_access_key
        return boto3.Session(**kwargs)

    def list_ec2_instances(self) -> list[dict[str, Any]]:
        ec2 = self._session().client("ec2")
        pages = ec2.get_paginator("describe_instances").paginate()
        instances: list[dict[str, Any]] = []
        for page in pages:
            for reservation in page["Reservations"]:
                instances.extend(reservation["Instances"])
        return instances

    def list_s3_buckets(self) -> list[dict[str, Any]]:
        s3 = self._session().client("s3")
        return s3.list_buckets().get("Buckets", [])

    def list_iam_roles(self) -> list[dict[str, Any]]:
        iam = self._session().client("iam")
        paginator = iam.get_paginator("list_roles")
        roles: list[dict[str, Any]] = []
        for page in paginator.paginate():
            roles.extend(page.get("Roles", []))
        return roles

    def list_rds_instances(self) -> list[dict[str, Any]]:
        rds = self._session().client("rds")
        paginator = rds.get_paginator("describe_db_instances")
        instances: list[dict[str, Any]] = []
        for page in paginator.paginate():
            instances.extend(page.get("DBInstances", []))
        return instances

    def list_lambda_functions(self) -> list[dict[str, Any]]:
        lmb = self._session().client("lambda")
        paginator = lmb.get_paginator("list_functions")
        functions: list[dict[str, Any]] = []
        for page in paginator.paginate():
            functions.extend(page.get("Functions", []))
        return functions

    def ping(self) -> bool:
        try:
            sts = self._session().client("sts")
            sts.get_caller_identity()
            return True
        except Exception:
            return False


class FakeAWSClient:
    """Canned data for unit tests and sandbox runs — no AWS credentials needed."""

    def __init__(self, fail_ping: bool = False) -> None:
        self._fail_ping = fail_ping

    def list_ec2_instances(self) -> list[dict[str, Any]]:
        return [
            {
                "InstanceId": "i-0abc123456",
                "InstanceType": "t3.medium",
                "State": {"Name": "running"},
                "Placement": {"AvailabilityZone": "us-east-1a"},
                "Tags": [{"Key": "Name", "Value": "web-server-prod"}],
            },
            {
                "InstanceId": "i-0def789012",
                "InstanceType": "t3.large",
                "State": {"Name": "running"},
                "Placement": {"AvailabilityZone": "us-east-1b"},
                "Tags": [{"Key": "Name", "Value": "worker-node-1"}],
            },
        ]

    def list_s3_buckets(self) -> list[dict[str, Any]]:
        return [
            {
                "Name": "aev-app-uploads-prod",
                "CreationDate": "2026-01-15T10:00:00Z",
                "PublicAccessBlock": {"BlockPublicAcls": False},
            },
            {
                "Name": "aev-audit-logs",
                "CreationDate": "2026-01-16T10:00:00Z",
                "PublicAccessBlock": {"BlockPublicAcls": True},
            },
        ]

    def list_iam_roles(self) -> list[dict[str, Any]]:
        return [
            {
                "RoleId": "AROAEXAMPLEID001",
                "RoleName": "ec2-ssm-role",
                "Arn": "arn:aws:iam::123456789012:role/ec2-ssm-role",
                "Path": "/",
            },
            {
                "RoleId": "AROAEXAMPLEID002",
                "RoleName": "legacy-admin",
                "Arn": "arn:aws:iam::123456789012:role/legacy-admin",
                "Path": "/",
            },
        ]

    def list_rds_instances(self) -> list[dict[str, Any]]:
        return [
            {
                "DBInstanceIdentifier": "aev-postgres-prod",
                "Engine": "postgres",
                "DBInstanceStatus": "available",
                "MultiAZ": True,
            },
        ]

    def list_lambda_functions(self) -> list[dict[str, Any]]:
        return [
            {
                "FunctionName": "aev-event-processor",
                "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:aev-event-processor",
                "Runtime": "python3.12",
                "LastModified": "2026-10-01T12:00:00.000+0000",
            },
        ]

    def ping(self) -> bool:
        return not self._fail_ping
