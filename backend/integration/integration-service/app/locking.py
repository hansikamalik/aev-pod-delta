"""
Distributed Locking Mechanism for Integration Service (P1-2).
Uses Redis mutex locking with Redlock semantics and graceful thread-safe in-memory fallback.
Prevents concurrent sync races on the same connector instance.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Dict, Optional

logger = logging.getLogger("integration_service.locking")


class SyncLockManager:
    """Manages distributed mutex locks per integration instance."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._redis_client = None
        self._memory_locks: Dict[str, Dict[str, Any]] = {}
        self._thread_lock = threading.Lock()
        self._init_redis()

    def _init_redis(self):
        try:
            import redis
            client = redis.Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
            )
            client.ping()
            self._redis_client = client
            logger.info("SyncLockManager connected to Redis at %s", self.redis_url)
        except Exception:
            self._redis_client = None
            logger.info("Redis not reachable; using in-memory distributed lock provider.")

    def acquire_lock(self, integration_id: str, job_id: str, ttl_seconds: int = 300) -> bool:
        """Acquire a mutex lock for the specified integration.
        Returns True if acquired; False if another sync job holds the lock.
        """
        key = f"lock:sync:{integration_id}"

        # 1. Try Redis first if available
        if self._redis_client is not None:
            try:
                # SET key job_id NX EX ttl_seconds
                acquired = bool(self._redis_client.set(key, job_id, nx=True, ex=ttl_seconds))
                if acquired:
                    logger.debug("Acquired Redis lock for '%s' (job: %s)", integration_id, job_id)
                return acquired
            except Exception as exc:
                logger.warning("Redis error acquiring lock for '%s': %s; falling back to in-memory", integration_id, exc)

        # 2. In-Memory fallback (thread-safe with expiration)
        now = time.time()
        with self._thread_lock:
            existing = self._memory_locks.get(integration_id)
            if existing:
                if now < existing["expires_at"]:
                    # Lock is still actively held by existing['job_id']
                    return False
                # Expired lock; safe to claim
                del self._memory_locks[integration_id]

            self._memory_locks[integration_id] = {
                "job_id": job_id,
                "expires_at": now + ttl_seconds,
            }
            logger.debug("Acquired memory lock for '%s' (job: %s)", integration_id, job_id)
            return True

    def get_active_job(self, integration_id: str) -> Optional[str]:
        """Return the job_id currently holding the lock for this integration, if any."""
        key = f"lock:sync:{integration_id}"

        if self._redis_client is not None:
            try:
                val = self._redis_client.get(key)
                if val:
                    return str(val)
            except Exception:
                pass

        now = time.time()
        with self._thread_lock:
            existing = self._memory_locks.get(integration_id)
            if existing and now < existing["expires_at"]:
                return str(existing["job_id"])
        return None

    def release_lock(self, integration_id: str, job_id: str) -> bool:
        """Release the mutex lock, ensuring only the job holding the lock can release it."""
        key = f"lock:sync:{integration_id}"

        if self._redis_client is not None:
            try:
                # Lua script for atomic compare-and-delete
                lua_script = """
                    if redis.call("get", KEYS[1]) == ARGV[1] then
                        return redis.call("del", KEYS[1])
                    else
                        return 0
                    end
                """
                res = self._redis_client.eval(lua_script, 1, key, job_id)
                return bool(res)
            except Exception as exc:
                logger.warning("Redis error releasing lock for '%s': %s", integration_id, exc)

        with self._thread_lock:
            existing = self._memory_locks.get(integration_id)
            if existing and existing.get("job_id") == job_id:
                del self._memory_locks[integration_id]
                return True
        return False

    def clear(self):
        """Reset all in-memory locks (used during testing)."""
        with self._thread_lock:
            self._memory_locks.clear()


# Global lock manager singleton
sync_lock_manager = SyncLockManager()
