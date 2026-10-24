"""
Discovery — searches Active Directory for user and group objects via
LDAP paged search (FR-INT-010: user/group sync).

ldap3's Connection is a blocking/synchronous client, so each page fetch
is run in a worker thread via asyncio.to_thread to keep this connector
non-blocking within the platform's async runtime.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from ldap3 import SUBTREE, Connection

from .auth import ADAuthClient
from .config import ActiveDirectoryConfig
from .exceptions import LDAPSearchError

USER_ATTRIBUTES = [
    "objectGUID",
    "distinguishedName",
    "sAMAccountName",
    "displayName",
    "mail",
    "userAccountControl",
    "memberOf",
    "whenChanged",
]

GROUP_ATTRIBUTES = [
    "objectGUID",
    "distinguishedName",
    "cn",
    "member",
    "groupType",
    "whenChanged",
]


def _fetch_all_pages(
    connection: Connection,
    search_base: str,
    search_filter: str,
    attributes: list[str],
    page_size: int,
) -> list[dict]:
    """Materialize a full paged LDAP search. Runs synchronously — always
    call this via asyncio.to_thread from async code."""
    try:
        generator = connection.extend.standard.paged_search(
            search_base=search_base,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=attributes,
            paged_size=page_size,
            generator=True,
        )
        return [entry for entry in generator if entry.get("type") == "searchResEntry"]
    except Exception as exc:  # noqa: BLE001 - normalize any ldap3 error
        raise LDAPSearchError(
            f"LDAP search failed (base='{search_base}', filter='{search_filter}'): {exc}"
        ) from exc


async def iter_users(config: ActiveDirectoryConfig, auth: ADAuthClient) -> AsyncIterator[dict]:
    """Yield raw LDAP user entries."""
    connection = await auth.get_connection()
    entries = await asyncio.to_thread(
        _fetch_all_pages,
        connection,
        config.resolved_user_search_base(),
        config.user_search_filter,
        USER_ATTRIBUTES,
        config.page_size,
    )
    for entry in entries:
        yield entry


async def iter_groups(config: ActiveDirectoryConfig, auth: ADAuthClient) -> AsyncIterator[dict]:
    """Yield raw LDAP group entries."""
    connection = await auth.get_connection()
    entries = await asyncio.to_thread(
        _fetch_all_pages,
        connection,
        config.resolved_group_search_base(),
        config.group_search_filter,
        GROUP_ATTRIBUTES,
        config.page_size,
    )
    for entry in entries:
        yield entry
