import time
from typing import Dict


class DistributedLockManager:
    """Prevents the same integration/connector from syncing twice concurrently."""
    
    _active_locks: Dict[str, float] = {}

    def acquire_lock(self, connector_id: str, timeout_seconds: int = 300) -> bool:
        current_time = time.time()
        if connector_id in self._active_locks:
            lock_expiry = self._active_locks[connector_id]
            if current_time < lock_expiry:
                return False  # Lock currently held
        
        self._active_locks[connector_id] = current_time + timeout_seconds
        return True

    def release_lock(self, connector_id: str) -> None:
        if connector_id in self._active_locks:
            del self._active_locks[connector_id]
