from datetime import datetime
from typing import Iterable, Dict, Any, Optional

from sdk.connector import Connector
from sdk.models import Asset, AssetType
from cyberark_auth_module.auth import CyberArkAuthModule
from .client import CyberArkClient


class CyberArkConnector(Connector):
    name: str = "cyberark"

    def __init__(
        self,
        config: Dict[str, Any],
        credentials: Dict[str, Any],
        platform_client: Optional[Any] = None,
    ):
        self.config = config
        self.credentials = credentials
        self._platform_client = platform_client

        self.auth = CyberArkAuthModule(
            base_url=self.config.get("url", ""),
            verify_tls=self.config.get("verify_tls", True),
        )
        self.client = CyberArkClient(
            auth_module=self.auth,
            base_url=self.config.get("url", ""),
            verify_tls=self.config.get("verify_tls", True),
        )

    def check_health(self) -> bool:
        try:
            token = self.auth.authenticate(self.credentials)
            return bool(token)
        except Exception:
            return False

    def describe_config(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "format": "uri"},
                "verify_tls": {"type": "boolean", "default": True},
            },
            "required": ["url"],
        }

    def describe_credentials(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "username": {"type": "string"},
                "password": {"type": "string", "secret": True},
            },
            "required": ["username", "password"],
        }

    def discover(self) -> Iterable[Asset]:
        if not self.auth.session_token:
            self.auth.authenticate(self.credentials)

        # 1. Discover CyberArk Accounts -> AssetType.IDENTITY
        for acct in self.client.list_accounts():
            yield Asset(
                id=f"{self.name}:account:{acct['id']}",
                source=self.name,
                type=AssetType.IDENTITY.value,
                name=acct.get("name", acct["id"]),
                raw=acct,
                discoveredAt=datetime.utcnow(),
                tags={"safeName": acct.get("safeName", "")},
            )

        # 2. Discover CyberArk Safes -> AssetType.STORAGE
        for safe in self.client.list_safes():
            yield Asset(
                id=f"{self.name}:safe:{safe.get('safeNumber', safe['safeName'])}",
                source=self.name,
                type=AssetType.STORAGE.value,
                name=f"Safe: {safe['safeName']}",
                raw=safe,
                discoveredAt=datetime.utcnow(),
            )

    def ingest(self, assets: Iterable[Asset]) -> int:
        asset_list = list(assets)
        if not asset_list:
            return 0

        if self._platform_client:
            self._platform_client.bulk_upsert(asset_list)

        return len(asset_list)
