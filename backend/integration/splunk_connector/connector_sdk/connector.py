"""Embedded Base Connector Abstract Class."""

from abc import ABC, abstractmethod
from typing import Iterable, Optional, Union
from .models import Asset, Checkpoint, SyncResult


class Connector(ABC):
    name: str = "base_connector"

    def __init__(self, config: dict, credentials: dict, platform_client=None):
        self.config = config
        self.credentials = credentials
        self.platform_client = platform_client

    @abstractmethod
    def describe_config(self) -> dict:
        pass

    @abstractmethod
    def describe_credentials(self) -> dict:
        pass

    @abstractmethod
    def check_health(self) -> bool:
        pass

    @abstractmethod
    def discover(
        self, checkpoint: Optional[Checkpoint] = None
    ) -> Iterable[Union[Asset, Checkpoint]]:
        pass

    async def sync(self, checkpoint: Optional[Checkpoint] = None) -> SyncResult:
        if not self.check_health():
            return SyncResult(status="failed", errors=["Health check failed"])

        assets = []
        latest_checkpoint = None

        try:
            for item in self.discover(checkpoint=checkpoint):
                if isinstance(item, Asset):
                    assets.append(item)
                elif isinstance(item, Checkpoint):
                    latest_checkpoint = item

            pushed_count = self.ingest(assets)

            if latest_checkpoint and self.platform_client:
                if hasattr(self.platform_client, "save_checkpoint"):
                    self.platform_client.save_checkpoint(self.name, latest_checkpoint)

            return SyncResult(
                status="success",
                assets_discovered=len(assets),
                assets_pushed=pushed_count,
                checkpoint=latest_checkpoint
            )
        except Exception as exc:
            return SyncResult(status="error", errors=[str(exc)])

    def ingest(self, assets: Iterable[Asset]) -> int:
        asset_list = list(assets)
        if self.platform_client and hasattr(self.platform_client, "bulk_upsert"):
            self.platform_client.bulk_upsert(asset_list)
        return len(asset_list)
