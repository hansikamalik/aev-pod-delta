import unittest

from microsoft365_connector.discovery import GraphDiscovery
from tests.sandbox.mock_graph_api import FakeGraphSession


def _discovery(fake_session=None):
    return GraphDiscovery(
        base_url="https://graph.microsoft.com/v1.0",
        get_access_token=lambda: "fake-token",
        session=fake_session or FakeGraphSession(),
    )


class TestGraphDiscovery(unittest.TestCase):
    def test_discover_resource_paginates_through_all_pages(self):
        discovery = _discovery()
        users = discovery.discover_resource("user")
        self.assertEqual([u["id"] for u in users], ["u-1", "u-2"])

    def test_discover_returns_all_requested_resources(self):
        discovery = _discovery()
        result = discovery.discover(["user", "group", "device", "domain", "license", "audit_log"])
        self.assertEqual(
            set(result.keys()), {"user", "group", "device", "domain", "license", "audit_log"}
        )
        self.assertEqual(len(result["group"]), 1)
        self.assertEqual(len(result["device"]), 1)
        self.assertEqual(len(result["domain"]), 1)
        self.assertEqual(len(result["license"]), 1)
        self.assertEqual(len(result["audit_log"]), 1)

    def test_discover_audit_logs_uses_directory_audits_endpoint(self):
        discovery = _discovery()
        entries = discovery.discover_audit_logs()
        self.assertEqual([e["id"] for e in entries], ["al-1"])

    def test_ingest_is_pass_through(self):
        discovery = _discovery()
        raw = {"user": [{"id": "u-1"}]}
        self.assertEqual(discovery.ingest(raw), raw)


if __name__ == "__main__":
    unittest.main()
