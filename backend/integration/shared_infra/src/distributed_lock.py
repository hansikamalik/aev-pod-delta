"""
Distributed Lock
Owner: Abhiram
Part of: Shared Integration Infrastructure

Design notes:
- Acquire/release semantics with TTL-based expiry so a crashed worker never
  holds a lock forever (auto-expiry instead of manual cleanup).
- Backed by MockLockBackend (in-memory dict) for independent dev; swap for
  a real backend (Redis SETNX, etcd, DynamoDB conditional write) later
  without changing DistributedLock's public interface.
- Used by scheduler.py to guarantee only one worker runs a given job at a
  time (duplicate-run prevention).
"""

from __future__ import annotations

import contextlib
import logging
import time
import uuid
from typing import Dict, Optional

logger = logging.getLogger("distributed_lock")


class LockAcquisitionError(Exception):
    """Raised when a lock is already held by someone else."""


class MockLockBackend:
    """
    In-memory lock store: {lock_name: (owner_token, expires_at_epoch)}
    Simulates atomic compare-and-set semantics a real backend would provide.
    """

    def __init__(self):
        self._locks: Dict[str, tuple] = {}

    def try_acquire(self, lock_name: str, owner_token: str, ttl_seconds: float, now: float) -> bool:
        existing = self._locks.get(lock_name)
        if existing is not None:
            existing_owner, expires_at = existing
            if now < expires_at and existing_owner != owner_token:
                return False  # held by someone else, not expired
        self._locks[lock_name] = (owner_token, now + ttl_seconds)
        return True

    def release(self, lock_name: str, owner_token: str) -> bool:
        existing = self._locks.get(lock_name)
        if existing is None:
            return False
        existing_owner, _ = existing
        if existing_owner != owner_token:
            return False  # can't release a lock you don't own
        del self._locks[lock_name]
        return True

    def is_locked(self, lock_name: str, now: Optional[float] = None) -> bool:
        now = now if now is not None else time.time()
        existing = self._locks.get(lock_name)
        if existing is None:
            return False
        _, expires_at = existing
        return now < expires_at


class DistributedLock:
    def __init__(self, backend, default_ttl_seconds: float = 30.0, clock: Optional[callable] = None):
        self.backend = backend
        self.default_ttl_seconds = default_ttl_seconds
        # Injectable clock so callers (e.g. schedulers/tests) can use a
        # fake/logical clock instead of wall-clock time.time().
        self._clock = clock or time.time

    def acquire_raw(self, lock_name: str, ttl_seconds: Optional[float] = None) -> str:
        """Returns an owner token on success; raises LockAcquisitionError on failure."""
        owner_token = uuid.uuid4().hex
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        now = self._clock()
        acquired = self.backend.try_acquire(lock_name, owner_token, ttl, now)
        if not acquired:
            raise LockAcquisitionError(f"Lock '{lock_name}' is already held")
        logger.info("Lock '%s' acquired by %s (ttl=%.1fs)", lock_name, owner_token, ttl)
        return owner_token

    def release_raw(self, lock_name: str, owner_token: str) -> None:
        released = self.backend.release(lock_name, owner_token)
        if released:
            logger.info("Lock '%s' released by %s", lock_name, owner_token)
        else:
            logger.warning("Lock '%s' release skipped — not owned by %s", lock_name, owner_token)

    @contextlib.contextmanager
    def acquire(self, lock_name: str, ttl_seconds: Optional[float] = None):
        owner_token = self.acquire_raw(lock_name, ttl_seconds)
        try:
            yield owner_token
        finally:
            self.release_raw(lock_name, owner_token)

    def is_locked(self, lock_name: str) -> bool:
        return self.backend.is_locked(lock_name, now=self._clock())
