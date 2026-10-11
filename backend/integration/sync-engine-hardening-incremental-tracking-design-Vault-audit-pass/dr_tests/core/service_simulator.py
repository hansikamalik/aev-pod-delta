import os
import time
import json
import signal
from pathlib import Path
from typing import Dict, Any

class IntegrationServiceSimulator:
    """Simulates the lifecycle, state checkpointing, and abrupt failure of the Integration Service."""

    def __init__(self, checkpoint_dir: str = "/tmp/sync_engine_checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.is_running = False

    def start_service(self) -> None:
        """Starts the mock Integration Service."""
        self.is_running = True

    def write_checkpoint(self, connector: str, job_id: str, last_processed_offset: int, payload_hash: str) -> Path:
        """Emulates in-flight state persistence before failure."""
        if not self.is_running:
            raise RuntimeError("Integration Service is down. Cannot write state checkpoint.")

        checkpoint_data = {
            "connector": connector,
            "job_id": job_id,
            "last_processed_offset": last_processed_offset,
            "payload_hash": payload_hash,
            "timestamp": time.time(),
            "status": "IN_PROGRESS",
            "vault_audit_status": "[REDACTED_VAULT_AUDIT]"
        }

        file_path = self.checkpoint_dir / f"{connector}_state.json"
        with open(file_path, "w") as f:
            json.dump(checkpoint_data, f, indent=2)
        return file_path

    def simulate_hard_crash(self) -> Dict[str, Any]:
        """Simulates an abrupt process crash (e.g., SIGKILL / OOM / Network Loss)."""
        if not self.is_running:
            return {"status": "ALREADY_DOWN"}
            
        self.is_running = False
        return {
            "status": "CRASHED",
            "signal": "SIGKILL",
            "timestamp": time.time(),
            "details": "Integration Service process terminated abruptly."
        }

    def recover_service(self) -> bool:
        """Simulates service restart and initialization from disk state."""
        self.is_running = True
        return self.is_running
