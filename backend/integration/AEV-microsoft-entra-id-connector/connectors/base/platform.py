"""Push client for the Beta platform asset/exposure service."""
from __future__ import annotations

import os
import time
from typing import Any

import requests

from .models import Asset, Finding

DEFAULT_BASE_URL = os.getenv("AEV_PLATFORM_URL", "http://localhost:8080/api/v1")


class PlatformPushError(RuntimeError):
    pass


class PlatformClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL,
                 api_key: str | None = None, max_retries: int = 3,
                 timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv("AEV_PLATFORM_API_KEY", "")
        self.max_retries = max_retries
        self.timeout = timeout
        self.session = requests.Session()
        if self.api_key:
            self.session.headers["Authorization"] = f"Bearer {self.api_key}"

    def _post(self, path: str, payload: dict[str, Any]) -> dict:
        url = f"{self.base_url}{path}"
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                resp = self.session.post(url, json=payload, timeout=self.timeout)
                if resp.status_code in (429, 500, 502, 503, 504):
                    time.sleep(0.5 * (2 ** attempt))  # backoff
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < self.max_retries - 1:
                    time.sleep(0.5 * (2 ** attempt))
        raise PlatformPushError(f"POST {url} failed after {self.max_retries} attempts: {last_exc}")

    def push_assets(self, assets: list[Asset]) -> int:
        if not assets:
            return 0
        resp = self._post("/assets/batch", {"assets": [a.to_dict() for a in assets]})
        return resp.get("accepted", len(assets))

    def push_findings(self, findings: list[Finding]) -> int:
        if not findings:
            return 0
        resp = self._post("/findings/batch", {"findings": [f.to_dict() for f in findings]})
        return resp.get("accepted", len(findings))

    def push(self, assets: list[Asset], findings: list[Finding]) -> dict:
        return {
            "assets": self.push_assets(assets),
            "findings": self.push_findings(findings),
        }
