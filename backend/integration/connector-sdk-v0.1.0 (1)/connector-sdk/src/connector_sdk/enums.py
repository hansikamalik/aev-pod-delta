"""Normalized enumerations defined by the Connector SDK contract.

Contract references:
  - Section 8  (Asset Type)
  - Section 15 (Sync Status)

New members MUST NOT be added by a connector. Adding a member is an SDK
contract change and requires review by the Integration Lead (Section 30).
"""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """A string enum that compares and serializes as its plain value.

    This lets connectors write ``type="compute"`` while the SDK still
    validates against a closed set. ``str(AssetType.COMPUTE) == "compute"``.
    """

    def __str__(self) -> str:  # pragma: no cover - trivial
        return str(self.value)


class AssetType(StrEnum):
    """Normalized asset categories (Section 8).

    Connectors map source-specific resource types onto these values, e.g.::

        EC2 instance      -> AssetType.COMPUTE
        S3 bucket         -> AssetType.STORAGE
        Okta user         -> AssetType.IDENTITY
        VPC               -> AssetType.NETWORK
        Jira issue        -> AssetType.TICKET
        Security alert    -> AssetType.DETECTION
        Unknown resource  -> AssetType.OTHER
    """

    COMPUTE = "compute"
    STORAGE = "storage"
    IDENTITY = "identity"
    NETWORK = "network"
    TICKET = "ticket"
    DETECTION = "detection"
    OTHER = "other"


class SyncStatus(StrEnum):
    """Outcome of exactly one synchronization attempt (Section 15).

    SUCCESS  - completed, everything discovered was pushed, no errors.
    PARTIAL  - completed, but some assets could not be processed.
    FAILED   - the synchronization could not perform the required operation.

    A connector MUST NOT report SUCCESS when assets were known to fail
    during ingestion.
    """

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


__all__ = ["AssetType", "SyncStatus", "StrEnum"]
