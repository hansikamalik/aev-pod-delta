"""
Cron-based Scheduling
Owner: Abhiram
Part of: Shared Integration Infrastructure

Design notes:
- Minimal, dependency-free cron-interval scheduler: register jobs with an
  interval (standing in for a full cron expression parser, swappable later
  without changing the job-triggering contract).
- Every job execution acquires the distributed lock (distributed_lock.py)
  before running, so the same job never runs concurrently across workers —
  this is developed and tested against a DUMMY connector, per the parallel
  rule, not against real Azure/Splunk connectors.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from distributed_lock import DistributedLock, LockAcquisitionError

logger = logging.getLogger("scheduler")


@dataclass
class ScheduledJob:
    name: str
    interval_seconds: float
    fn: Callable[[], None]
    last_run: Optional[float] = None
    run_count: int = 0
    skipped_duplicate_runs: int = 0

    def is_due(self, now: float) -> bool:
        return self.last_run is None or (now - self.last_run) >= self.interval_seconds


class CronScheduler:
    """
    Tick-based scheduler: call `tick()` on your own loop/timer. This keeps
    the module testable without sleeping in real time.
    """

    def __init__(self, lock: DistributedLock):
        self.lock = lock
        self._jobs: Dict[str, ScheduledJob] = {}

    def register_job(self, name: str, interval_seconds: float, fn: Callable[[], None]) -> None:
        if name in self._jobs:
            raise ValueError(f"Job '{name}' already registered")
        self._jobs[name] = ScheduledJob(name=name, interval_seconds=interval_seconds, fn=fn)
        logger.info("Registered job '%s' every %.1fs", name, interval_seconds)

    def tick(self, now: Optional[float] = None) -> List[str]:
        """
        Runs all due jobs exactly once each, guarded by the distributed lock
        to prevent duplicate concurrent execution. Returns names of jobs
        that actually ran this tick.
        """
        now = now if now is not None else time.time()
        ran = []
        for job in self._jobs.values():
            if not job.is_due(now):
                continue
            lock_name = f"job:{job.name}"
            try:
                with self.lock.acquire(lock_name):
                    job.fn()
                    job.run_count += 1
                    job.last_run = now
                    ran.append(job.name)
                    logger.info("Job '%s' executed (run #%d)", job.name, job.run_count)
            except LockAcquisitionError:
                job.skipped_duplicate_runs += 1
                logger.warning(
                    "Job '%s' skipped — lock held elsewhere (duplicate-run prevention, skip #%d)",
                    job.name, job.skipped_duplicate_runs,
                )
        return ran

    def status(self) -> Dict[str, dict]:
        return {
            name: {
                "run_count": job.run_count,
                "last_run": job.last_run,
                "skipped_duplicate_runs": job.skipped_duplicate_runs,
            }
            for name, job in self._jobs.items()
        }
