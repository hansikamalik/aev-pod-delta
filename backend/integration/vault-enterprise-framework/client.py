from typing import Dict, List, Any
import requests


class VaultEnterpriseClient:
    """HTTP client wrapper for Vault Enterprise APIs."""

    def __init__(
        self,
        vault_addr: str,
        namespace: str = "root",
        token: str = None,
        verify_tls: bool = True,
    ):
        self.vault_addr = vault_addr.rstrip("/") if vault_addr else ""
        self.namespace = namespace
        self.token = token
        self.verify_tls = verify_tls

    def _headers(self) -> Dict[str, str]:
        headers = {}
        if self.token:
            headers["X-Vault-Token"] = self.token
        if self.namespace and self.namespace != "root":
            headers["X-Vault-Namespace"] = self.namespace
        return headers

    def ping(self) -> bool:
        url = f"{self.vault_addr}/v1/sys/health"
        resp = requests.get(url, verify=self.verify_tls, timeout=5)
        return resp.status_code in (200, 429, 501, 503)

    def list_namespaces(self) -> List[Dict[str, Any]]:
        url = f"{self.vault_addr}/v1/sys/namespaces?LIST=true"
        resp = requests.get(url, headers=self._headers(), verify=self.verify_tls)
        if resp.status_code == 200:
            keys = resp.json().get("data", {}).get("keys", [])
            return [{"id": k.strip("/"), "path": k} for k in keys]
        return []

    def list_secret_engines(self) -> Dict[str, Any]:
        url = f"{self.vault_addr}/v1/sys/mounts"
        resp = requests.get(url, headers=self._headers(), verify=self.verify_tls)
        if resp.status_code == 200:
            return resp.json().get("data", {})
        return {}
