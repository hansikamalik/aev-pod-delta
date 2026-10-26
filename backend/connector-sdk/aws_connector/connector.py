"""
AWS Connector — discovers EC2 instances, S3 buckets, IAM roles,
RDS database instances, and Lambda functions from an AWS account.

Production usage: set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
and AWS_DEFAULT_REGION in environment or pass them explicitly.

For unit tests / sandbox use FakeAWSClient, which returns canned
data with the same shape — no network access needed.
"""

from __future__ import annotations

from typing import Any, Iterable

from connector_sdk import Asset, AssetType, Connector

from .client import AWSAPIClient, AWSClientProtocol, FakeAWSClient


class AWSConnector(Connector):
    """Discovers compute, storage, identity, and serverless assets
    from an AWS account and normalises them into the platform Asset schema.
    """

    name = "aws"

    def __init__(
        self,
        region: str = "us-east-1",
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        client: AWSClientProtocol | None = None,
    ) -> None:
        """
        Args:
            region:           AWS region to query (default us-east-1).
            access_key_id:    AWS Access Key ID. Falls back to env var
                              AWS_ACCESS_KEY_ID if not supplied.
            secret_access_key: AWS Secret Access Key. Falls back to env var
                               AWS_SECRET_ACCESS_KEY if not supplied.
            client:           Optional pre-built API client (used by tests).
        """
        self.region = region
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._client = client

    # -- internal helpers ------------------------------------------------

    def _get_client(self) -> AWSClientProtocol:
        if self._client is not None:
            return self._client
        self._client = AWSAPIClient(
            region=self.region,
            access_key_id=self._access_key_id,
            secret_access_key=self._secret_access_key,
        )
        return self._client

    @staticmethod
    def _normalize_ec2(instance: dict[str, Any]) -> Asset:
        name = next(
            (t["Value"] for t in instance.get("Tags", []) if t["Key"] == "Name"),
            instance["InstanceId"],
        )
        return Asset(
            id=instance["InstanceId"],
            source="aws",
            type=AssetType.COMPUTE,
            name=name,
            raw=instance,
            tags={
                "region": instance.get("Placement", {}).get("AvailabilityZone", ""),
                "state": instance.get("State", {}).get("Name", ""),
                "instance_type": instance.get("InstanceType", ""),
            },
        )

    @staticmethod
    def _normalize_s3(bucket: dict[str, Any]) -> Asset:
        return Asset(
            id=bucket["Name"],
            source="aws",
            type=AssetType.STORAGE,
            name=bucket["Name"],
            raw=bucket,
            tags={
                "creation_date": str(bucket.get("CreationDate", "")),
                "public_access": str(bucket.get("PublicAccessBlock", {}).get("BlockPublicAcls", True)),
            },
        )

    @staticmethod
    def _normalize_iam_role(role: dict[str, Any]) -> Asset:
        return Asset(
            id=role["RoleId"],
            source="aws",
            type=AssetType.IDENTITY,
            name=role["RoleName"],
            raw=role,
            tags={
                "arn": role.get("Arn", ""),
                "path": role.get("Path", "/"),
            },
        )

    @staticmethod
    def _normalize_rds(db: dict[str, Any]) -> Asset:
        return Asset(
            id=db["DBInstanceIdentifier"],
            source="aws",
            type=AssetType.STORAGE,
            name=db["DBInstanceIdentifier"],
            raw=db,
            tags={
                "engine": db.get("Engine", ""),
                "status": db.get("DBInstanceStatus", ""),
                "multi_az": str(db.get("MultiAZ", False)),
            },
        )

    @staticmethod
    def _normalize_lambda(fn: dict[str, Any]) -> Asset:
        return Asset(
            id=fn["FunctionArn"],
            source="aws",
            type=AssetType.COMPUTE,
            name=fn["FunctionName"],
            raw=fn,
            tags={
                "runtime": fn.get("Runtime", ""),
                "last_modified": fn.get("LastModified", ""),
            },
        )

    # -- Connector interface ---------------------------------------------

    def discover(self) -> Iterable[Asset]:
        """Discover EC2 instances, S3 buckets, IAM roles, RDS instances,
        and Lambda functions from the configured AWS account.
        """
        client = self._get_client()
        assets: list[Asset] = []

        for instance in client.list_ec2_instances():
            assets.append(self._normalize_ec2(instance))

        for bucket in client.list_s3_buckets():
            assets.append(self._normalize_s3(bucket))

        for role in client.list_iam_roles():
            assets.append(self._normalize_iam_role(role))

        for db in client.list_rds_instances():
            assets.append(self._normalize_rds(db))

        for fn in client.list_lambda_functions():
            assets.append(self._normalize_lambda(fn))

        return assets

    def ingest(self, assets: Iterable[Asset]) -> int:
        """Push discovered assets to the platform asset service."""
        assets = list(assets)
        # In production: call the platform's bulk_upsert API.
        # The platform client is injected here; for simplicity the
        # connector returns the count — wiring to the real platform
        # HTTP client is done at the integration-service layer.
        return len(assets)

    def check_health(self) -> bool:
        """Verify AWS credentials and network reachability."""
        try:
            return self._get_client().ping()
        except Exception:
            return False

    def describe_config(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "description": "AWS region to query, e.g. us-east-1",
                    "default": "us-east-1",
                },
            },
            "required": ["region"],
        }

    def describe_credentials(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "access_key_id": {
                    "type": "string",
                    "secret": True,
                    "description": "AWS Access Key ID",
                },
                "secret_access_key": {
                    "type": "string",
                    "secret": True,
                    "description": "AWS Secret Access Key",
                },
            },
            "required": ["access_key_id", "secret_access_key"],
        }
