"""
Discovery tests use a hand-rolled fake connection rather than ldap3's
MOCK_SYNC strategy, because MOCK_SYNC documents support for bind/search/
add/modify/compare/delete — not the paged-search extended operation
this module relies on for large directories. Faking
`connection.extend.standard.paged_search` directly keeps these tests
fast and decoupled from that uncertainty while still exercising the
real page-materializing and yielding logic in discovery.py.
"""

import pytest

from active_directory_connector.discovery import iter_groups, iter_users


class _FakeStandardExtension:
    def __init__(self, entries):
        self._entries = entries

    def paged_search(self, **kwargs):
        # Mirrors ldap3's generator=True behavior: yields dict entries,
        # each tagged with a 'type', filtering out non-entry results.
        for entry in self._entries:
            yield entry


class _FakeExtend:
    def __init__(self, entries):
        self.standard = _FakeStandardExtension(entries)


class FakeConnection:
    def __init__(self, entries):
        self.extend = _FakeExtend(entries)


class FakeAuth:
    def __init__(self, connection: FakeConnection):
        self._connection = connection

    async def get_connection(self, force_rebind: bool = False):
        return self._connection


USER_ENTRIES = [
    {
        "type": "searchResEntry",
        "dn": "CN=Jane Doe,OU=Users,DC=corp,DC=example,DC=com",
        "attributes": {
            "objectGUID": "guid-user-1",
            "distinguishedName": "CN=Jane Doe,OU=Users,DC=corp,DC=example,DC=com",
            "sAMAccountName": "jdoe",
            "displayName": "Jane Doe",
            "mail": "jdoe@corp.example.com",
            "userAccountControl": "512",
            "memberOf": ["CN=Engineering,OU=Groups,DC=corp,DC=example,DC=com"],
            "whenChanged": "20260101120000.0Z",
        },
    },
    {"type": "searchResDone"},  # should be filtered out
]

GROUP_ENTRIES = [
    {
        "type": "searchResEntry",
        "dn": "CN=Engineering,OU=Groups,DC=corp,DC=example,DC=com",
        "attributes": {
            "objectGUID": "guid-group-1",
            "distinguishedName": "CN=Engineering,OU=Groups,DC=corp,DC=example,DC=com",
            "cn": "Engineering",
            "member": ["CN=Jane Doe,OU=Users,DC=corp,DC=example,DC=com"],
            "groupType": "-2147483646",
            "whenChanged": "20260101120000.0Z",
        },
    },
]


@pytest.mark.asyncio
async def test_iter_users_yields_only_entries_not_done_markers(ad_config):
    auth = FakeAuth(FakeConnection(USER_ENTRIES))

    users = [u async for u in iter_users(ad_config, auth)]

    assert len(users) == 1
    assert users[0]["attributes"]["sAMAccountName"] == "jdoe"


@pytest.mark.asyncio
async def test_iter_groups_yields_entries(ad_config):
    auth = FakeAuth(FakeConnection(GROUP_ENTRIES))

    groups = [g async for g in iter_groups(ad_config, auth)]

    assert len(groups) == 1
    assert groups[0]["attributes"]["cn"] == "Engineering"


@pytest.mark.asyncio
async def test_iter_users_empty_directory_yields_nothing(ad_config):
    auth = FakeAuth(FakeConnection([]))

    users = [u async for u in iter_users(ad_config, auth)]

    assert users == []
