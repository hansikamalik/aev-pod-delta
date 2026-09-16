from typing import Dict, Any, Union
from src.auth import CyberArkAuthManager
from src.ccp import CyberArkCCPClient
from src.oauth import CyberArkIdentityOAuthClient
from src.exceptions import CyberArkAuthError

AuthClientType = Union[CyberArkAuthManager, CyberArkCCPClient, CyberArkIdentityOAuthClient]


class CyberArkAuthFactory:
    """Factory interface for instantiating CyberArk authentication providers."""

    @staticmethod
    def create_client(config: Dict[str, Any]) -> AuthClientType:
        auth_type = config.get("auth_type", "").lower()
        verify_ssl = config.get("verify_ssl", True)
        timeout = config.get("timeout", 10)

        if auth_type == "interactive":
            if "pas_url" not in config:
                raise CyberArkAuthError("Missing parameter 'pas_url' for interactive authentication.")
            
            client = CyberArkAuthManager(pas_url=config["pas_url"], verify_ssl=verify_ssl, timeout=timeout)
            if "username" in config and "password" in config:
                client.authenticate(username=config["username"], password=config["password"], use_radius=config.get("use_radius", False))
            return client

        elif auth_type == "ccp":
            if "ccp_url" not in config or "app_id" not in config:
                raise CyberArkAuthError("Missing required parameters ('ccp_url', 'app_id') for CCP authentication.")
            
            return CyberArkCCPClient(
                ccp_url=config["ccp_url"],
                app_id=config["app_id"],
                client_cert=config.get("client_cert"),
                verify_ssl=verify_ssl,
                timeout=timeout
            )

        elif auth_type == "oauth2":
            required_keys = ["tenant_url", "client_id", "client_secret"]
            missing = [k for k in required_keys if k not in config]
            if missing:
                raise CyberArkAuthError(f"Missing required parameters {missing} for OAuth2 authentication.")

            client = CyberArkIdentityOAuthClient(
                tenant_url=config["tenant_url"],
                client_id=config["client_id"],
                client_secret=config["client_secret"],
                token_endpoint_path=config.get("token_endpoint_path", "/oauth2/token"),
                verify_ssl=verify_ssl,
                timeout=timeout
            )
            client.get_token()
            return client

        else:
            raise CyberArkAuthError(f"Unsupported 'auth_type': '{auth_type}'. Choose from ['interactive', 'ccp', 'oauth2'].")
