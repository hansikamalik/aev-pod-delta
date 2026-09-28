"""
Push normalized assets/findings to the platform's ingest endpoints.
"""

from typing import Any, Callable, Dict, List, Optional

import requests

from .exceptions import PushError
from .models import Asset, Finding


class PlatformClient:
    def __init__(
        self,
        base_url: str,
        get_api_token: Callable[[], str],
        ingest_endpoint: str = "/api/v1/assets/ingest",
        findings_endpoint: str = "/api/v1/findings/ingest",
        batch_size: int = 100,
        timeout: float = 15.0,
        session: Optional[requests.Session] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.get_api_token = get_api_token
        self.ingest_endpoint = ingest_endpoint
        self.findings_endpoint = findings_endpoint
        self.batch_size = batch_size
        self.timeout = timeout
        self.session = session or requests.Session()

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.get_api_token()}",
            "Content-Type": "application/json",
        }

    def _push_batched(
        self, url: str, items: List[Any], payload_key: str, source_connector: str
    ) -> Dict[str, Any]:
        pushed = 0
        failed_batches = []

        for start in range(0, len(items), self.batch_size):
            batch = items[start : start + self.batch_size]
            payload = {
                "source_connector": source_connector,
                payload_key: [item.to_dict() for item in batch],
            }
            try:
                resp = self.session.post(
                    url, json=payload, headers=self._headers(), timeout=self.timeout
                )
                resp.raise_for_status()
            except requests.RequestException as exc:
                failed_batches.append({"batch_start": start, "error": str(exc)})
                continue
            pushed += len(batch)

        if failed_batches:
            raise PushError(
                f"{pushed}/{len(items)} {payload_key} pushed; {len(failed_batches)} "
                f"batch(es) failed: {failed_batches}"
            )

        return {"pushed": pushed, "total": len(items)}

    def push(self, assets: List[Asset]) -> Dict[str, Any]:
        url = f"{self.base_url}{self.ingest_endpoint}"
        return self._push_batched(url, assets, "assets", "microsoft_365")

    def push_findings(self, findings: List[Finding]) -> Dict[str, Any]:
        url = f"{self.base_url}{self.findings_endpoint}"
        return self._push_batched(url, findings, "findings", "microsoft_365")
