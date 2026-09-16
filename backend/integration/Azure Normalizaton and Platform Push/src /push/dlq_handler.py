import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any


class DLQHandler:
    """Handles persistence of failed assets to Dead Letter Queue (DLQ) storage."""

    def __init__(self, dlq_dir: str = "dlq_output") -> None:
        self.dlq_dir = dlq_dir
        os.makedirs(self.dlq_dir, exist_ok=True)

    def write_to_dlq(self, failed_assets: List[Dict[str, Any]], reason: str) -> str:
        """
        Writes failed asset payloads along with error reason and timestamp to a DLQ file.
        
        :param failed_assets: List of rejected asset dictionaries.
        :param reason: Error cause (e.g., SCHEMA_VALIDATION_ERROR, HTTP_429_EXHAUSTED).
        :return: Path to the generated DLQ log file.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        file_path = os.path.join(self.dlq_dir, f"dlq_batch_{timestamp}.json")

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "failed_count": len(failed_assets),
            "assets": failed_assets
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)

        return file_path
