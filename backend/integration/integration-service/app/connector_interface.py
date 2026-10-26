"""
Canonical Connector interface re-exported from shared connector_sdk.
Reconciled for P1-5.
"""

from connector_sdk import (
    Asset,
    AssetType,
    AsyncConnector,
    Connector,
    SyncResult,
    SyncStatus,
)

__all__ = [
    "Connector",
    "AsyncConnector",
    "Asset",
    "AssetType",
    "SyncResult",
    "SyncStatus",
]
