from typing import Any, Mapping, Optional

from azure.identity import ClientSecretCredential


class AzureServicePrincipalAuthenticator:
    """
    Minimal Azure Service Principal authentication support for the
    Integration auth module.

    The connector credential schema remains provisional until the
    Connector SDK squad finalizes the shared contract.
    """

    def __init__(
        self,
        auth_data: Mapping[str, Any],
        tenant_id: str,
        subscription_ids: Optional[list[str]] = None,
    ):
        self.auth_data = auth_data
        self.tenant_id = tenant_id
        self.subscription_ids = subscription_ids
        self._credential: Optional[ClientSecretCredential] = None

    def get_credential(self) -> ClientSecretCredential:
        if self._credential is None:
            self._credential = self._build_credential()
        return self._credential

    def _build_credential(self) -> ClientSecretCredential:
        client_id = self.auth_data.get("client_id")
        client_secret = self.auth_data.get("client_secret")

        if not client_id:
            raise ValueError("Missing Service Principal client_id.")

        if not client_secret:
            raise ValueError("Missing Service Principal client_secret.")

        if not self.tenant_id:
            raise ValueError("Missing tenant_id.")

        # PROVISIONAL — INFORM SDK SQUAD:
        # client_id/client_secret are internal keys only.
        # Final connector credential schema is not fixed.
        return ClientSecretCredential(
            tenant_id=self.tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )

    def get_subscription_ids(self) -> Optional[list[str]]:
        """
        Return explicitly supplied subscription IDs.

        PROVISIONAL — INFORM SDK SQUAD:
        subscription handling is intentionally separate from
        credential data and is not the final connector schema.
        """
        return self.subscription_ids