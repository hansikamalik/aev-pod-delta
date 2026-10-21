import json
import os
from typing import Dict, Any


class CheckpointStore:
    """Manages per-resource-type high-water marks and timestamps for resumability."""

    def __init__(self, storage_path: str = "test_checkpoint.json"):
        self.storage_path = storage_path

    def load_checkpoint(self, connector_id: str, resource_type: str = "default_resource") -> Dict[str, Any]:
        if not os.path.exists(self.storage_path):
            return {}
        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
                return data.get(connector_id, {}).get(resource_type, {})
        except Exception:
            return {}

    def save_checkpoint(self, connector_id: str, resource_type: str, checkpoint_data: Dict[str, Any]) -> None:
        all_data = {}
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    all_data = json.load(f)
            except Exception:
                all_data = {}
        
        if connector_id not in all_data:
            all_data[connector_id] = {}
        
        all_data[connector_id][resource_type] = checkpoint_data
        with open(self.storage_path, "w") as f:
            json.dump(all_data, f, indent=2)
