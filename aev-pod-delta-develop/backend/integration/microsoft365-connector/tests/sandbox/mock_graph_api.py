"""
Local sandbox: fixtures + a fake requests.Session for testing the Microsoft
365 connector fully offline. Mirrors the "Python sandbox v2" pattern from
the sprint plan (mock API server, no real vendor calls) — swap for the
squad's shared sandbox once it lands (Week 3, Connector SDK).
"""

from typing import Any, Dict, List

SAMPLE_USERS_PAGE_1 = {
    "value": [
        {
            "id": "u-1",
            "displayName": "Asha Rao",
            "userPrincipalName": "asha.rao@contoso.com",
            "mail": "asha.rao@contoso.com",
            "accountEnabled": True,
            "jobTitle": "Analyst",
            "department": "Risk",
        }
    ],
    "@odata.nextLink": "https://graph.microsoft.com/v1.0/users?$skiptoken=PAGE2",
}

SAMPLE_USERS_PAGE_2 = {
    "value": [
        {
            "id": "u-2",
            "displayName": "Devon Lee",
            "userPrincipalName": "devon.lee@contoso.com",
            "mail": "devon.lee@contoso.com",
            "accountEnabled": False,
            "jobTitle": "Contractor",
            "department": "IT",
        }
    ]
    # no nextLink: last page
}

SAMPLE_GROUPS = {
    "value": [
        {
            "id": "g-1",
            "displayName": "Security Admins",
            "securityEnabled": True,
            "mailEnabled": False,
            "groupTypes": [],
        }
    ]
}

SAMPLE_DEVICES = {
    "value": [
        {
            "id": "d-1",
            "displayName": "ASHA-LAPTOP",
            "operatingSystem": "Windows",
            "operatingSystemVersion": "11",
            "accountEnabled": True,
            "trustType": "AzureAd",
            "isCompliant": True,
            "isManaged": True,
            "registeredOwners": ["asha.rao@contoso.com"],
        }
    ]
}

SAMPLE_DOMAINS = {
    "value": [
        {
            "id": "contoso.com",
            "isVerified": True,
            "isDefault": True,
            "supportedServices": ["Email", "OfficeCommunicationsOnline"],
        }
    ]
}

SAMPLE_LICENSES = {
    "value": [
        {
            "skuId": "sku-1",
            "skuPartNumber": "ENTERPRISEPACK",
            "consumedUnits": 42,
            "capabilityStatus": "Enabled",
            "prepaidUnits": {"enabled": 50, "suspended": 0, "warning": 0},
        }
    ]
}

SAMPLE_AUDIT_LOGS = {
    "value": [
        {
            "id": "al-1",
            "category": "UserManagement",
            "correlationId": "corr-1",
            "result": "success",
            "resultReason": "",
            "activityDisplayName": "Add user",
            "activityDateTime": "2026-09-20T10:15:00Z",
            "loggedByService": "Core Directory",
            "operationType": "Add",
            "initiatedBy": {
                "user": {
                    "id": "admin-1",
                    "displayName": "Admin User",
                    "userPrincipalName": "admin@contoso.com",
                }
            },
            "targetResources": [{"id": "u-2", "displayName": "Devon Lee", "type": "User"}],
        }
    ]
}

RESOURCE_FIXTURES = {
    "/users": [SAMPLE_USERS_PAGE_1, SAMPLE_USERS_PAGE_2],
    "/groups": [SAMPLE_GROUPS],
    "/devices": [SAMPLE_DEVICES],
    "/domains": [SAMPLE_DOMAINS],
    "/subscribedSkus": [SAMPLE_LICENSES],
    "/auditLogs/directoryAudits": [SAMPLE_AUDIT_LOGS],
}


class FakeResponse:
    def __init__(self, json_body: Dict[str, Any], status_code: int = 200):
        self._json = json_body
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._json


class FakeGraphSession:
    """
    Fake `requests.Session` that serves RESOURCE_FIXTURES, handling
    pagination via a simple page-cursor per resource path.
    """

    def __init__(self, resource_fixtures: Dict[str, List[Dict[str, Any]]] = None):
        self._fixtures = resource_fixtures or RESOURCE_FIXTURES
        self._page_index: Dict[str, int] = {}

    def get(self, url: str, headers=None, params=None, timeout=None):
        resource_path = self._match_resource(url)
        idx = self._page_index.get(resource_path, 0)
        pages = self._fixtures[resource_path]
        body = pages[min(idx, len(pages) - 1)]
        self._page_index[resource_path] = idx + 1
        return FakeResponse(body)

    def post(self, url: str, json=None, headers=None, timeout=None):
        return FakeResponse({"status": "accepted"}, status_code=202)

    def _match_resource(self, url: str) -> str:
        for path in self._fixtures:
            if path in url:
                return path
        raise KeyError(f"No fixture registered for URL: {url}")
