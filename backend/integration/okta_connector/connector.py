"""
Okta Connector.

Owner: Bhavesh Kanekar (Week 3, Integration Squad).

Implements the shared six-method Connector interface against Okta's
Users and Groups APIs:
  - Authentication: token-based (SSWS), via OktaCredentials
  - discover(): pulls all users and all groups (with membership)
  - normalize(): maps them into the shared Asset shape
  - sync(): discover -> normalize -> push, returns a SyncResult
  - health_check(): confirms the token/org URL work
  - describe_config() / describe_credentials(): schema for the UI/config layer
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .client import OktaAPIError, OktaClient
from .credentials import OktaCredentials, describe_credential_schema
from .models import Asset, AssetStatus, AssetType, Connector, SyncResult

CONNECTOR_NAME = "okta"


def _user_status_to_asset_status(okta_status: str) -> AssetStatus:
    # Okta user statuses: STAGED, PROVISIONED, ACTIVE, RECOVERY, PASSWORD_EXPIRED,
    # LOCKED_OUT, SUSPENDED, DEPROVISIONED
    active_statuses = {"ACTIVE", "PROVISIONED", "PASSWORD_EXPIRED", "RECOVERY"}
    inactive_statuses = {"SUSPENDED", "LOCKED_OUT", "DEPROVISIONED", "STAGED"}
    if okta_status in active_statuses:
        return AssetStatus.ACTIVE
    if okta_status in inactive_statuses:
        return AssetStatus.INACTIVE
    return AssetStatus.UNKNOWN


class OktaConnector(Connector):
    def __init__(
        self,
        credentials: OktaCredentials,
        client: Optional[OktaClient] = None,
        push_fn: Optional[Callable[[List[Asset]], int]] = None,
    ):
        """
        push_fn: callable that sends normalized assets to the platform's
        asset service and returns how many were accepted. Injected so it
        can be swapped for a mock/no-op in tests and local dev, and wired
        to the real asset-service client in production.
        """
        self._creds = credentials
        self._client = client or OktaClient(credentials)
        self._push_fn = push_fn or self._default_push

    # -- Connector interface -------------------------------------------------

    def discover(self) -> List[Dict[str, Any]]:
        """Pull all users and all groups (each group tagged with its members)."""
        raw_records: List[Dict[str, Any]] = []

        for user in self._client.list_users():
            raw_records.append({"_okta_type": "user", **user})

        for group in self._client.list_groups():
            group_id = group.get("id")
            members = self._client.list_group_members(group_id) if group_id else []
            raw_records.append(
                {
                    "_okta_type": "group",
                    "_member_ids": [m.get("id") for m in members if m.get("id")],
                    **group,
                }
            )

        return raw_records

    def normalize(self, raw_records: List[Dict[str, Any]]) -> List[Asset]:
        assets: List[Asset] = []
        for record in raw_records:
            record_type = record.get("_okta_type")
            if record_type == "user":
                assets.append(self._normalize_user(record))
            elif record_type == "group":
                assets.append(self._normalize_group(record))
            # Unrecognized record types are skipped rather than raising --
            # discover() controls what shapes reach here.
        return assets

    def sync(self) -> SyncResult:
        started_at = datetime.now(timezone.utc)
        errors: List[str] = []
        assets: List[Asset] = []

        try:
            raw_records = self.discover()
            assets = self.normalize(raw_records)
        except OktaAPIError as exc:
            errors.append(str(exc))

        pushed = 0
        if assets and not errors:
            try:
                pushed = self._push_fn(assets)
            except Exception as exc:  # pragma: no cover - defensive
                errors.append(f"push failed: {exc}")

        return SyncResult(
            connector=CONNECTOR_NAME,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
            assets_discovered=len(assets),
            assets_pushed=pushed,
            errors=errors,
        )

    def health_check(self) -> bool:
        return self._client.health_check()

    def describe_config(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sync_interval_minutes": {
                    "type": "integer",
                    "default": 60,
                    "description": "How often the cron scheduler should run this connector",
                },
                "include_deprovisioned_users": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether to ingest deprovisioned users as inactive assets",
                },
            },
        }

    def describe_credentials(self) -> Dict[str, Any]:
        return describe_credential_schema()

    # -- helpers ---------------------------------------------------------

    def _normalize_user(self, record: Dict[str, Any]) -> Asset:
        profile = record.get("profile", {})
        display_name = " ".join(
            filter(None, [profile.get("firstName"), profile.get("lastName")])
        ) or profile.get("login", record.get("id", "unknown-user"))

        return Asset(
            external_id=record["id"],
            source=CONNECTOR_NAME,
            asset_type=AssetType.USER,
            name=display_name,
            status=_user_status_to_asset_status(record.get("status", "")),
            attributes={
                "login": profile.get("login"),
                "email": profile.get("email"),
                "department": profile.get("department"),
                "title": profile.get("title"),
                "okta_status": record.get("status"),
                "created": record.get("created"),
                "last_login": record.get("lastLogin"),
            },
        )

    def _normalize_group(self, record: Dict[str, Any]) -> Asset:
        profile = record.get("profile", {})
        return Asset(
            external_id=record["id"],
            source=CONNECTOR_NAME,
            asset_type=AssetType.GROUP,
            name=profile.get("name", record.get("id", "unknown-group")),
            status=AssetStatus.ACTIVE,
            attributes={
                "description": profile.get("description"),
                "member_ids": record.get("_member_ids", []),
                "member_count": len(record.get("_member_ids", [])),
                "type": record.get("type"),
            },
        )

    @staticmethod
    def _default_push(assets: List[Asset]) -> int:
        """No-op push used until this is wired to the real asset service."""
        return len(assets)
