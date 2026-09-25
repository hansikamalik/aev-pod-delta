from unittest.mock import MagicMock

from sentinel_connector.base import Asset
from sentinel_connector.push import BetaPlatformPusher


def make_assets(n):
    return [
        Asset(external_id=f"a{i}", source="microsoft_sentinel", asset_type="endpoint", name=f"host-{i}")
        for i in range(n)
    ]


def test_push_success_single_batch():
    session = MagicMock()
    session.post.return_value = MagicMock(status_code=200)

    pusher = BetaPlatformPusher(api_token="tok", session=session)
    result = pusher.push("microsoft_sentinel", make_assets(5))

    assert result.success is True
    assert result.assets_count == 5
    assert session.post.call_count == 1


def test_push_batches_large_asset_lists():
    session = MagicMock()
    session.post.return_value = MagicMock(status_code=201)

    pusher = BetaPlatformPusher(api_token="tok", session=session)
    result = pusher.push("microsoft_sentinel", make_assets(450), batch_size=200)

    assert result.assets_count == 450
    assert session.post.call_count == 3  # 200 + 200 + 50


def test_push_records_errors_on_failed_batch():
    session = MagicMock()
    resp_fail = MagicMock(status_code=500, text="server error")
    session.post.return_value = resp_fail

    pusher = BetaPlatformPusher(api_token="tok", session=session)
    result = pusher.push("microsoft_sentinel", make_assets(3))

    assert result.success is False
    assert result.assets_count == 0
    assert len(result.errors) == 1
