"""Microsoft Entra ID discovery ΓÇö Week 2 deliverable.

Enumerates the three object types Pod Delta tracks for identity
providers via Microsoft Graph: users, groups, service principals.
Built on top of Week 1's EntraIDAuth (auth.py) for token handling.
"""
from __future__ import annotations

import requests

from connectors.microsoft_entra_id.auth import EntraIDAuth

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
PAGE_SIZE = 100

# object_type -> Graph list endpoint
OBJECT_ENDPOINTS = {
    "user": "/users",
    "group": "/groups",
    "service_principal": "/servicePrincipals",
}


class EntraIDDiscoveryError(RuntimeError):
    pass


def _paginate(auth: EntraIDAuth, endpoint: str, object_type: str,
              session: requests.Session | None = None) -> list[dict]:
    """Follow @odata.nextLink until exhausted, tagging each item's source type."""
    session = session or auth.session
    url = f"{GRAPH_BASE}{endpoint}?$top={PAGE_SIZE}"
    items: list[dict] = []

    while url:
        resp = session.get(url, headers=auth.headers(), timeout=30)
        if resp.status_code != 200:
            raise EntraIDDiscoveryError(
                f"Graph list failed for {object_type}: {resp.status_code} {resp.text[:200]}"
            )
        body = resp.json()
        for obj in body.get("value", []):
            obj["_object_type"] = object_type
            items.append(obj)
        url = body.get("@odata.nextLink")

    return items


def discover_raw(auth: EntraIDAuth) -> list[dict]:
    """Enumerate raw users, groups, and service principals from Graph."""
    raw_items: list[dict] = []
    for object_type, endpoint in OBJECT_ENDPOINTS.items():
        raw_items.extend(_paginate(auth, endpoint, object_type))
    return raw_items
