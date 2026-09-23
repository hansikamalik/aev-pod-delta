import time
import random
import requests
from typing import List, Dict, Any, Optional, Tuple
from src.interfaces.base_push_engine import BasePushEngine
from src.push.dlq_handler import DLQHandler


class PlatformPushEngine(BasePushEngine):
    """Pushes normalized assets to platform ingestion API with retries, backoff with jitter, and DLQ support."""

    def __init__(
        self,
        endpoint_url: str,
        api_key: str,
        batch_size: int = 100,
        max_retries: int = 3,
        base_backoff_sec: float = 1.0,
        dlq_dir: str = "dlq_output"
    ) -> None:
        self.endpoint_url = endpoint_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.base_backoff_sec = base_backoff_sec
        self.dlq_handler = DLQHandler(dlq_dir=dlq_dir)

    def push_batch(self, assets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Pushes assets in chunked batches. Ships valid chunks to HTTP API and routes failures to DLQ.
        """
        total = len(assets)
        successful = 0
        failed = 0
        dlq_files: List[str] = []

        # Process in chunks of batch_size (default 100)
        for i in range(0, total, self.batch_size):
            chunk = assets[i:i + self.batch_size]
            success, failure_reason = self._send_chunk_with_retry(chunk)

            if success:
                successful += len(chunk)
            else:
                failed += len(chunk)
                dlq_file = self.route_to_dlq(chunk, reason=failure_reason)
                dlq_files.append(dlq_file)

        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "dlq_files": dlq_files
        }

    def route_to_dlq(self, failed_assets: List[Dict[str, Any]], reason: str) -> str:
        """Routes failed chunk assets directly to Dead Letter Queue."""
        return self.dlq_handler.write_to_dlq(failed_assets, reason)

    def _send_chunk_with_retry(self, chunk: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Executes HTTP POST request with Exponential Backoff + Full Jitter for 429 & 5xx statuses.
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.post(
                    self.endpoint_url,
                    json={"assets": chunk},
                    headers=self.headers,
                    timeout=15.0
                )

                if response.status_code in (200, 201, 202):
                    return True, "SUCCESS"

                # Rate Limiting (429) or Server Errors (5xx) -> Eligible for Retry
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt == self.max_retries:
                        return False, f"HTTP_{response.status_code}_MAX_RETRIES_EXCEEDED"
                    
                    self._sleep_exponential_jitter(attempt)
                    continue

                # Client side error (400 Bad Request, 401 Unauthorized, 403 Forbidden) -> Do NOT retry
                return False, f"HTTP_{response.status_code}_CLIENT_ERROR"

            except requests.RequestException as e:
                if attempt == self.max_retries:
                    return False, f"NETWORK_ERROR_MAX_RETRIES_EXCEEDED: {str(e)}"
                self._sleep_exponential_jitter(attempt)

        return False, "UNKNOWN_FAILURE"

    def _sleep_exponential_jitter(self, attempt: int) -> None:
        """Calculates backoff duration using Exponential Backoff with Full Jitter."""
        temp = self.base_backoff_sec * (2 ** (attempt - 1))
        sleep_duration = random.uniform(0, temp)
        time.sleep(sleep_duration)
