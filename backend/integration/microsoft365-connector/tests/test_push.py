import unittest
from unittest.mock import MagicMock

import requests

from microsoft365_connector.exceptions import PushError
from microsoft365_connector.models import Asset, AssetStatus, AssetType, Finding
from microsoft365_connector.push import PlatformClient


def _asset(i: int) -> Asset:
    return Asset(
        asset_id=f"a-{i}",
        asset_type=AssetType.USER,
        display_name=f"User {i}",
        source_connector="microsoft_365",
        status=AssetStatus.ENABLED,
    )


def _finding(i: int) -> Finding:
    return Finding(
        finding_id=f"f-{i}",
        finding_type="audit_log",
        source_connector="microsoft_365",
        activity=f"Event {i}",
    )


class TestPlatformClient(unittest.TestCase):
    def test_push_batches_correctly(self):
        session = MagicMock()
        session.post.return_value.raise_for_status.return_value = None

        client = PlatformClient(
            base_url="https://api.aev.internal",
            get_api_token=lambda: "token",
            batch_size=2,
            session=session,
        )
        result = client.push([_asset(i) for i in range(5)])

        self.assertEqual(result, {"pushed": 5, "total": 5})
        self.assertEqual(session.post.call_count, 3)

    def test_push_raises_and_reports_partial_success_on_failure(self):
        session = MagicMock()
        responses = [MagicMock(), requests.RequestException("boom")]

        def post_side_effect(*args, **kwargs):
            result = responses.pop(0)
            if isinstance(result, Exception):
                raise result
            result.raise_for_status.return_value = None
            return result

        session.post.side_effect = post_side_effect

        client = PlatformClient(
            base_url="https://api.aev.internal",
            get_api_token=lambda: "token",
            batch_size=2,
            session=session,
        )

        with self.assertRaises(PushError) as ctx:
            client.push([_asset(i) for i in range(4)])

        self.assertIn("2/4 assets pushed", str(ctx.exception))

    def test_push_findings_batches_correctly_and_uses_findings_endpoint(self):
        session = MagicMock()
        session.post.return_value.raise_for_status.return_value = None

        client = PlatformClient(
            base_url="https://api.aev.internal",
            get_api_token=lambda: "token",
            findings_endpoint="/api/v1/findings/ingest",
            batch_size=10,
            session=session,
        )
        result = client.push_findings([_finding(i) for i in range(3)])

        self.assertEqual(result, {"pushed": 3, "total": 3})
        called_url = session.post.call_args.args[0]
        self.assertTrue(called_url.endswith("/api/v1/findings/ingest"))
        payload = session.post.call_args.kwargs["json"]
        self.assertIn("findings", payload)
        self.assertEqual(len(payload["findings"]), 3)


if __name__ == "__main__":
    unittest.main()
