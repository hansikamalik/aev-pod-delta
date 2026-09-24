class ADConnectorError(Exception):
    """Base exception for all Active Directory connector errors."""


class LDAPBindError(ADConnectorError):
    """Raised when the LDAP simple bind to the domain controller fails
    (bad credentials, disabled service account, unreachable DC)."""


class VaultAccessError(ADConnectorError):
    """Raised when connector credentials cannot be retrieved from Vault.

    This connector cannot bind to Active Directory without Vault
    access — the service account's bind password, referenced by
    IntegrationConfig.credentials_ref, lives in Vault (Alpha), never in
    connector config. See README.md > Dependencies.
    """


class LDAPSearchError(ADConnectorError):
    """Raised when an LDAP search operation fails or returns a
    non-success result code."""


class PushError(ADConnectorError):
    """Raised when pushing normalized assets to the platform's Asset
    service (Beta) fails."""
