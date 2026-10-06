from typing import Dict, List, Any
from datetime import datetime, timezone
from sync_engine.models import Asset, Checkpoint


class MockPlatformClient:
    def __init__(self):
        self.checkpoints: Dict[str, Checkpoint] = {}
        self.pushed_assets: Dict[str, List[Asset]] = {}

    def get_checkpoint(self, connector_id: str) -> Checkpoint:
        if connector_id not in self.checkpoints:
            return Checkpoint(
                connector_id=connector_id,
                high_water_mark=datetime(1970, 1, 1, tzinfo=timezone.utc),
            )
        return self.checkpoints[connector_id]

    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        self.checkpoints[checkpoint.connector_id] = checkpoint

    def push_assets(self, connector_id: str, assets: List[Asset]) -> None:
        if connector_id not in self.pushed_assets:
            self.pushed_assets[connector_id] = []
        self.pushed_assets[connector_id].extend(assets)

    def save_assets(self, connector_id: str, assets: List[Asset]) -> None:
        self.push_assets(connector_id, assets)
