import functools
import logging
import requests
from src.exceptions import CyberArkAuthError

logger = logging.getLogger(__name__)


def with_auto_refresh(max_retries=1):
    """Decorator to automatically retry API calls when an HTTP 401 occurs by refreshing credentials."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            attempts = 0
            while attempts <= max_retries:
                try:
                    return func(self, *args, **kwargs)
                except requests.HTTPError as e:
                    if e.response is not None and e.response.status_code == 401 and attempts < max_retries:
                        attempts += 1
                        logger.warning(
                            f"Received HTTP 401 Unauthorized. Attempting token refresh (Attempt {attempts}/{max_retries})..."
                        )
                        auth_client = getattr(self, "auth_client", None) or self
                        try:
                            # Trigger token refresh or session renewal
                            if hasattr(auth_client, "get_token"):
                                auth_client.get_token(force_refresh=True)
                            elif hasattr(auth_client, "login"):
                                auth_client.login()
                            elif hasattr(auth_client, "get_auth_headers"):
                                auth_client.get_auth_headers()
                            else:
                                raise CyberArkAuthError("Auth client has no supported re-authentication method")
                        except CyberArkAuthError:
                            raise
                        except Exception as refresh_err:
                            logger.error(f"Auto-refresh failed during re-authentication: {refresh_err}")
                            raise CyberArkAuthError(f"Auto-refresh failed: {refresh_err}") from refresh_err
                        continue
                    raise
        return wrapper
    return decorator
