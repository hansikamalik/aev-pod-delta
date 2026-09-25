"""Retry scheduling: exponential backoff with full jitter."""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from .config import RetryPolicy


def should_retry(policy: RetryPolicy, attempt: int, status_code: int | None, error: str | None) -> bool:
    """Decide whether attempt N should be followed by another one.

    ``attempt`` is 1-based. A transport error (no status code) is always
    retryable; an HTTP response is retryable only for the configured codes.
    """
    if attempt >= policy.max_attempts:
        return False
    if status_code is None:
        return error is not None
    return status_code in policy.retry_status_codes


def backoff_delay(policy: RetryPolicy, attempt: int, rng: random.Random | None = None) -> float:
    """Delay in seconds before attempt ``attempt + 1`` (``attempt`` is 1-based)."""
    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    raw = policy.base_delay_seconds * (policy.multiplier ** (attempt - 1))
    capped = min(raw, policy.max_delay_seconds)
    if not policy.jitter:
        return capped
    r = rng or random
    return r.uniform(0.0, capped)


def next_retry_at(
    policy: RetryPolicy,
    attempt: int,
    now: datetime | None = None,
    rng: random.Random | None = None,
) -> datetime:
    base = now or datetime.now(UTC)
    return base + timedelta(seconds=backoff_delay(policy, attempt, rng))
