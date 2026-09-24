"""Connector configuration model.

`config` is the non-secret JSON blob stored on the `integrations` table
(see integrations.config JSONB). `credentials_ref` on that same table
points at the Vault path holding the bind password — it is never
present here.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ActiveDirectoryConfig(BaseModel):
    ldap_server: str = Field(..., description="Domain controller hostname or IP")
    ldap_port: int = Field(default=636, description="389 for LDAP, 636 for LDAPS")
    use_ssl: bool = Field(default=True, description="Use LDAPS (recommended)")

    bind_dn: str = Field(
        ..., description="Service account DN used for the LDAP simple bind, e.g. "
        "'CN=svc-aev-sync,OU=Service Accounts,DC=corp,DC=example,DC=com'"
    )
    base_dn: str = Field(..., description="Root DN of the domain, e.g. 'DC=corp,DC=example,DC=com'")

    user_search_base: str | None = Field(
        default=None, description="Defaults to base_dn if not set"
    )
    user_search_filter: str = Field(default="(&(objectClass=user)(objectCategory=person))")

    group_search_base: str | None = Field(
        default=None, description="Defaults to base_dn if not set"
    )
    group_search_filter: str = Field(default="(objectClass=group)")

    sync_groups: bool = Field(default=True, description="Whether to also sync group objects")
    page_size: int = Field(default=500, ge=1, le=1000, description="LDAP paged-search page size")
    connect_timeout_seconds: float = Field(default=10.0, gt=0)
    receive_timeout_seconds: float = Field(default=30.0, gt=0)

    def resolved_user_search_base(self) -> str:
        return self.user_search_base or self.base_dn

    def resolved_group_search_base(self) -> str:
        return self.group_search_base or self.base_dn
