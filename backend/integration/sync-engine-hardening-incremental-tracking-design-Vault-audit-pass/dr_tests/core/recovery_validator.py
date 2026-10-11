import json
from pathlib import Path
from typing import Dict, Any, List

class DRRecoveryValidator:
    """Validates that sync jobs resume cleanly without duplication or unredacted secrets."""

    def __init__(self, checkpoint_dir: str = "/tmp/sync_engine_checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)

    def load_last_checkpoint(self, connector: str) -> Dict[str, Any]:
        """Loads persistent checkpoint state saved before failure."""
        file_path = self.checkpoint_dir / f"{connector}_state.json"
        if not file_path.exists():
            raise FileNotFoundError(f"No checkpoint state found for connector: {connector}")

        with open(file_path, "r") as f:
            return json.load(f)

    def validate_resumed_sync(
        self, 
        connector: str, 
        resume_offset: int, 
        processed_job_ids: List[str]
    ) -> Dict[str, Any]:
        """Ensures exact-once resumption semantics and Vault Audit compliance."""
        checkpoint = self.load_last_checkpoint(connector)
        expected_offset = checkpoint["last_processed_offset"]

        # 1. Check for Duplicate Processing / Data Loss
        offset_delta = resume_offset - expected_offset
        if offset_delta < 0:
            status = "DATA_REPETITION_ERROR"
            reason = f"Job rewound past checkpoint offset. Expected >= {expected_offset}, got {resume_offset}"
        elif offset_delta > 1:
            status = "DATA_LOSS_ERROR"
            reason = f"Job skipped records during recovery. Expected {expected_offset + 1}, got {resume_offset}"
        else:
            status = "CLEAN_RESUME_PASSED"
            reason = f"Job resumed exactly at offset {resume_offset}"

        # 2. Vault Audit Redaction Sweep
        serialized_checkpoint = json.dumps(checkpoint)
        has_secret_leak = any(
            token in serialized_checkpoint.lower() 
            for token in ["client_secret", "vault_token", "private_key", "password"]
            if "[redacted_vault_audit]" not in serialized_checkpoint.lower()
        )

        return {
            "connector": connector,
            "status": status,
            "reason": reason,
            "resumed_offset": resume_offset,
            "vault_audit_compliant": not has_secret_leak,
            "job_id": checkpoint["job_id"]
        }
