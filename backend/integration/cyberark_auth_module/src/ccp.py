import requests
from typing import Dict, Any, Optional, Tuple, Union
from src.exceptions import CyberArkAuthError


class CyberArkCCPClient:
    """Client for retrieving secrets from CyberArk Central Credential Provider (CCP)."""

    def __init__(
        self,
        ccp_url: str,
        app_id: str,
        client_cert: Optional[Union[str, Tuple[str, str]]] = None,
        verify_ssl: bool = True,
        timeout: int = 10
    ):
        self.ccp_url = ccp_url
        self.app_id = app_id
        self.client_cert = client_cert
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.session = requests.Session()

    def get_credential(self, safe: str, object_name: str, folder: Optional[str] = None) -> Dict[str, Any]:
        """Retrieves object secrets directly from CCP over HTTP/mTLS."""
        params = {
            "AppID": self.app_id,
            "Safe": safe,
            "Object": object_name
        }
        if folder:
            params["Folder"] = folder

        try:
            resp = self.session.get(
                self.ccp_url,
                params=params,
                cert=self.client_cert,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            if resp.status_code != 200:
                raise CyberArkAuthError(f"CCP Secret retrieval failed [HTTP {resp.status_code}]: {resp.text}")
            
            return resp.json()

        except requests.RequestException as exc:
            raise CyberArkAuthError(f"Network error querying CCP: {str(exc)}") from exc
