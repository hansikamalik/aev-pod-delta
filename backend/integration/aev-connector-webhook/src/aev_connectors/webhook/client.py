"""Outbound delivery client.

Delivers a signed event to a subscriber, retrying with exponential backoff and
writing every attempt to the delivery log.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import UTC, datetime

import httpx

from .auth import build_auth_headers
from .config import WebhookConfig
from .delivery_log import DeliveryLog
from .models import DeliveryAttempt, DeliveryRecord, DeliveryStatus, Event, Subscription
from .retry import backoff_delay, should_retry
from .signing import ATTEMPT_HEADER, DELIVERY_ID_HEADER, EVENT_ID_HEADER, EVENT_TYPE_HEADER

logger = logging.getLogger(__name__)


class DeliveryClient:
    """Signs, sends, retries, and logs one event per subscription."""

    def __init__(
        self,
        config: WebhookConfig,
        delivery_log: DeliveryLog,
        http_client: httpx.AsyncClient | None = None,
        sleep=asyncio.sleep,
    ) -> None:
        self._config = config
        self._log = delivery_log
        self._client = http_client
        self._owns_client = http_client is None
        self._sleep = sleep

    async def __aenter__(self) -> DeliveryClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._config.timeout_seconds,
                verify=self._config.verify_tls,
            )
        return self

    async def __aexit__(self, *exc_info) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def _serialize(event: Event) -> bytes:
        return json.dumps(event.envelope(), separators=(",", ":"), sort_keys=True).encode()

    async def ping(self) -> bool:
        """Health check: HEAD the target URL, treat any HTTP reply as reachable."""
        if self._client is None:
            raise RuntimeError("DeliveryClient used outside an async context manager")
        try:
            response = await self._client.head(self._config.target_url)
        except httpx.HTTPError as exc:  # noqa: BLE001 handled — narrow httpx base
            logger.warning("webhook ping failed for %s: %s", self._config.target_url, exc)
            return False
        return response.status_code < 500

    async def deliver(self, event: Event, subscription: Subscription) -> DeliveryRecord:
        """Deliver one event, retrying per policy. Always returns a logged record."""
        if self._client is None:
            raise RuntimeError("DeliveryClient used outside an async context manager")

        body = self._serialize(event)
        target = str(subscription.target_url)
        record = self._log.append(
            DeliveryRecord(
                org_id=event.org_id,
                connector_id=self._config.connector_id,
                subscription_id=subscription.id,
                event_id=event.id,
                event_type=event.event_type,
                target_url=target,
            )
        )
        policy = self._config.retry

        for attempt in range(1, policy.max_attempts + 1):
            headers = {
                "Content-Type": "application/json",
                EVENT_ID_HEADER: event.id,
                EVENT_TYPE_HEADER: event.event_type,
                DELIVERY_ID_HEADER: record.id,
                ATTEMPT_HEADER: str(attempt),
                **build_auth_headers(self._config, body),
            }

            started = time.perf_counter()
            status_code: int | None = None
            error: str | None = None
            try:
                response = await self._client.post(target, content=body, headers=headers)
                status_code = response.status_code
            except httpx.HTTPError as exc:
                error = f"{type(exc).__name__}: {exc}"

            duration_ms = int((time.perf_counter() - started) * 1000)

            if status_code is not None and 200 <= status_code < 300:
                record.record_attempt(
                    DeliveryAttempt(attempt=attempt, status_code=status_code, duration_ms=duration_ms),
                    DeliveryStatus.DELIVERED,
                )
                record.next_retry_at = None
                return record

            retryable = should_retry(policy, attempt, status_code, error)
            record.record_attempt(
                DeliveryAttempt(
                    attempt=attempt,
                    status_code=status_code,
                    error=error,
                    duration_ms=duration_ms,
                ),
                DeliveryStatus.RETRYING if retryable else DeliveryStatus.FAILED,
            )

            if not retryable:
                if attempt >= policy.max_attempts:
                    record.status = DeliveryStatus.DEAD_LETTERED
                record.next_retry_at = None
                logger.warning(
                    "webhook delivery %s gave up after %s attempt(s): status=%s error=%s",
                    record.id,
                    attempt,
                    status_code,
                    error,
                )
                return record

            delay = backoff_delay(policy, attempt)
            record.next_retry_at = datetime.now(UTC)
            await self._sleep(delay)

        record.status = DeliveryStatus.DEAD_LETTERED
        return record
