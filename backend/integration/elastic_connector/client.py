import time
from typing import Any, Dict, List, Optional
import requests


class ElasticClient:
    def __init__(
        self,
        endpoint: str,
        api_key: str,
        timeout: int = 30,
        verify_ssl: bool = True,
        max_retries: int = 3,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.max_retries = max_retries

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"ApiKey {self.api_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.endpoint}{path}"
        headers = self._headers()
        
        for attempt in range(self.max_retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                    **kwargs,
                )
                if response.status_code in (429, 502, 503, 504) and attempt < self.max_retries - 1:
                    time.sleep(0.1)
                    continue
                response.raise_for_status()
                return response.json()
            except requests.RequestException:
                if attempt == self.max_retries - 1:
                    raise

    def ping(self) -> bool:
        try:
            self._request("GET", "/")
            return True
        except Exception:
            return False

    def list_nodes(self) -> List[Dict[str, Any]]:
        try:
            res = self._request("GET", "/_nodes")
            if not isinstance(res, dict):
                return []
            nodes = res.get("nodes", {})
            if not isinstance(nodes, dict):
                return []
            return [{"node_id": node_id, **(details if isinstance(details, dict) else {})} for node_id, details in nodes.items()]
        except Exception:
            return []

    def list_indices(self) -> List[Dict[str, Any]]:
        try:
            res = self._request("GET", "/_cat/indices?format=json")
            return res if isinstance(res, list) else []
        except Exception:
            return []

    def list_transforms(self) -> List[Dict[str, Any]]:
        try:
            res = self._request("GET", "/_transform")
            if not isinstance(res, dict):
                return []
            transforms = res.get("transforms", [])
            return transforms if isinstance(transforms, list) else []
        except Exception:
            return []
