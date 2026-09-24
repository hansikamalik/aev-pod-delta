import requests
from typing import Dict, Any, List, Optional


class SplunkAPIError(Exception):
    """Custom exception raised when Splunk API operations fail."""
    pass


class SplunkClient:
    def __init__(self, host: str, bearer_token: str, port: int = 8089, verify_ssl: bool = True):
        self.base_url = f"https://{host}:{port}"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/x-www-form-urlencoded"
        })
        self.verify_ssl = verify_ssl

    def ping(self) -> bool:
        try:
            response = self.session.get(
                f"{self.base_url}/services/server/info",
                params={"output_mode": "json"},
                verify=self.verify_ssl,
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False

    def create_search_job(self, query: str, earliest_time: Optional[str] = None) -> str:
        payload = {
            "search": query if query.startswith("search") else f"search {query}",
            "output_mode": "json"
        }
        if earliest_time:
            payload["earliest_time"] = earliest_time

        try:
            response = self.session.post(
                f"{self.base_url}/services/search/jobs",
                data=payload,
                verify=self.verify_ssl,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data["sid"]
        except Exception as e:
            raise SplunkAPIError(f"Failed to create search job: {e}") from e

    def get_search_results(self, sid: str, count: int = 100) -> List[Dict[str, Any]]:
        try:
            response = self.session.get(
                f"{self.base_url}/services/search/jobs/{sid}/results",
                params={"output_mode": "json", "count": count},
                verify=self.verify_ssl,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except Exception as e:
            raise SplunkAPIError(f"Failed to retrieve search results: {e}") from e

    def forward_events(self, events: List[Dict[str, Any]]) -> bool:
        try:
            response = self.session.post(
                f"{self.base_url}/services/receivers/stream",
                json=events,
                verify=self.verify_ssl,
                timeout=30
            )
            response.raise_for_status()
            return True
        except Exception as e:
            raise SplunkAPIError(f"Failed to forward events: {e}") from e
