"""
LDAP simple-bind authentication against Active Directory
(FR-INT-010: Active Directory — LDAP bind; user/group sync). Depends
on credentials.VaultCredentialProvider for the service account's bind
password.
"""

from __future__ import annotations

from ldap3 import ALL, Connection, Server

from .config import ActiveDirectoryConfig
from .credentials import VaultCredentialProvider
from .exceptions import LDAPBindError


class ADAuthClient:
    """Creates and rebinds LDAP connections to the domain controller."""

    def __init__(
        self,
        config: ActiveDirectoryConfig,
        credential_provider: VaultCredentialProvider,
        client_strategy: str | None = None,
    ):
        self._config = config
        self._credentials = credential_provider
        self._connection: Connection | None = None
        # Only ever set in tests, to swap in ldap3's in-memory MOCK_SYNC
        # strategy instead of opening a real socket to a domain controller.
        self._client_strategy = client_strategy

    async def get_connection(self, *, force_rebind: bool = False) -> Connection:
        if not force_rebind and self._connection is not None and self._connection.bound:
            return self._connection

        creds = await self._credentials.get_credentials(force_refresh=force_rebind)

        server = Server(
            self._config.ldap_server,
            port=self._config.ldap_port,
            use_ssl=self._config.use_ssl,
            get_info=ALL,
            connect_timeout=self._config.connect_timeout_seconds,
        )
        connection_kwargs: dict = dict(
            user=self._config.bind_dn,
            password=creds.bind_password,
            receive_timeout=self._config.receive_timeout_seconds,
        )
        if self._client_strategy is not None:
            connection_kwargs["client_strategy"] = self._client_strategy

        connection = Connection(server, **connection_kwargs)

        try:
            bound = connection.bind()
        except Exception as exc:  # noqa: BLE001 - normalize any ldap3/socket error
            raise LDAPBindError(f"LDAP bind to {self._config.ldap_server} failed: {exc}") from exc

        if not bound:
            # A failed bind (as opposed to a network error) usually means the
            # service account password was rotated — force Vault re-read next time.
            self._credentials.invalidate()
            result = getattr(connection, "result", {})
            raise LDAPBindError(
                f"LDAP bind rejected for '{self._config.bind_dn}': "
                f"{result.get('description', 'unknown error')}"
            )

        self._connection = connection
        return connection

    def unbind(self) -> None:
        if self._connection is not None:
            try:
                self._connection.unbind()
            except Exception:  # noqa: BLE001 - best-effort cleanup
                pass
            self._connection = None
