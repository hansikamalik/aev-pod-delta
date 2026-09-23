import json

import pytest

from connectors.servicenow.client import ServiceNowClient, ServiceNowAPIError
from connectors.servicenow.auth import ServiceNowAuth


class _Resp:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self._payload = payload or {}
        self.text = json.dumps(self._payload)
        self.content = b"{}"

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = 0

    def request(self, method, url, headers=None, timeout=None, **kw):
        self.calls += 1
        if not self.pages:
            return _Resp(200, {"result": []})
        return self.pages.pop(0)


def _auth():
    return ServiceNowAuth("https://x.service-now.com", method="basic",
                          username="u", password="p")


def test_pagination_collects_all_pages():
    pages = [
        _Resp(200, {"result": [{"sys_id": str(i)} for i in range(200)]}),
        _Resp(200, {"result": [{"sys_id": "200"}]}),
    ]
    client = ServiceNowClient(_auth(), session=FakeSession(pages))
    records = list(client.get_table("cmdb_ci", batch_size=200))
    assert len(records) == 201


def test_empty_first_page_yields_nothing():
    client = ServiceNowClient(_auth(), session=FakeSession([_Resp(200, {"result": []})]))
    assert list(client.get_table("cmdb_ci")) == []


def test_4xx_raises():
    client = ServiceNowClient(_auth(), session=FakeSession([_Resp(403, {})]))
    with pytest.raises(ServiceNowAPIError):
        list(client.get_table("cmdb_ci"))
