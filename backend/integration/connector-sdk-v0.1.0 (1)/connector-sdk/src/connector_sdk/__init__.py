"""Connector SDK — common contract for platform integrations.

Implements the interface defined in ``contract_v2.md``. Every connector
MUST extend :class:`Connector` and pass the shared contract test suite in
``connector_sdk.testing`` before merge.

Quick start::

    from connector_sdk import Asset, AssetType, Connector

    class MyConnector(Connector):
        name = "mysource"

        def discover(self):
            for item in self._client.list_items():
                yield Asset(
                    id=item["id"],
                    source=self.name,
                    type=AssetType.COMPUTE,
                    name=item["name"],
                    raw=item,
                )

        def ingest(self, assets):
            assets = list(assets)
            return self._platform.bulk_upsert(assets)

        def check_health(self) -> bool: ...
        def describe_config(self) -> dict: ...
        def describe_credentials(self) -> dict: ...
"""

from .connector import Connector
from .enums import AssetType, SyncStatus
from .exceptions import (
    AuthenticationError,
    ConfigurationError,
    ConnectorError,
    ContractViolation,
    CredentialError,
    DiscoveryError,
    IngestionError,
    RateLimitError,
    SourceError,
    SourceUnavailableError,
    ValidationError,
)
from .models import Asset, SyncResult, build_asset_id, utcnow
from .schemas import (
    assert_valid_schema,
    field,
    object_schema,
    redact,
    secret_field,
    validate_against_schema,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # core
    "Connector",
    "Asset",
    "SyncResult",
    "AssetType",
    "SyncStatus",
    # helpers
    "build_asset_id",
    "utcnow",
    "object_schema",
    "field",
    "secret_field",
    "assert_valid_schema",
    "validate_against_schema",
    "redact",
    # errors
    "ConnectorError",
    "ConfigurationError",
    "CredentialError",
    "AuthenticationError",
    "SourceError",
    "SourceUnavailableError",
    "RateLimitError",
    "DiscoveryError",
    "IngestionError",
    "ValidationError",
    "ContractViolation",
]
