import logging
from typing import Any, Dict, Generator, List, Optional
import requests

logger = logging.getLogger(__name__)


class QRadarClient:
    """Client for interacting with QRadar REST API v19+."""

    def __init__(self, host: str, sec_token: str, verify_ssl: bool = True, api_version: str = "19.0"):
        self.base_url = f"https://{host.rstrip('/')}/api"
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.headers.update({
            "SEC": sec_token,
            "Version": api_version,
            "Accept": "application/json"
        })

    def ping(self) -> bool:
        """Lightweight check to verify reachability and authentication."""
        endpoint = f"{self.base_url}/system/about"
        try:
            response = self.session.get(endpoint, timeout=10, verify=self.verify_ssl)
            return response.status_code == 200
        except Exception as exc:
            logger.error(f"Health check failed during request to {endpoint}: {exc}")
            return False

    def list_assets(self, page_size: int = 50) -> Generator[Dict[str, Any], None, None]:
        """
        Retrieves asset models from QRadar with range header-based pagination.
        Handles rate limits (HTTP 429) gracefully.
        """
        endpoint = f"{self.base_url}/asset_model/assets"
        start = 0
        
        while True:
            end = start + page_size - 1
            headers = {"Range": f"items={start}-{end}"}
            
            try:
                response = self.session.get(
                    endpoint,
                    headers=headers,
                    timeout=30,
                    verify=self.verify_ssl
                )

                if response.status_code == 429:
                    logger.warning("QRadar rate limit hit. Raising for retry layer handling.")
                    response.raise_for_status()

                if response.status_code in (200, 206):
                    items = response.json()
                    if not items:
                        break
                    for item in items:
                        yield item
                    
                    if len(items) < page_size:
                        break
                    
                    start += page_size
                elif response.status_code == 416:
                    break
                else:
                    response.raise_for_status()

            except requests.RequestException as exc:
                logger.error(f"Error fetching assets from QRadar: {exc}")
                raise


class MockPlatformClient:
    """Simulated Platform Asset Service client for ingestion."""

    def bulk_upsert(self, assets: List[Any]) -> int:
        return len(assets)
