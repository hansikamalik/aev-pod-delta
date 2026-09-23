from unittest.mock import MagicMock

import requests

from gitlab_connector.base import Asset
from gitlab_connector.push import BetaPlatformPusher


def make_assets(n):
    return [Asset(external_id=str(i), source="gitlab", asset_type="repository", name=f"acme/p{i}") for i in range(n)]


def test_single_batch_success():
    s = MagicMock()
    s.post.return_value = MagicMock(status_code=200)
    r = BetaPlatformPusher("tok", session=s).push("gitlab", make_assets(5))
    assert r.success and r.assets_count == 5 and s.post.call_count == 1


def test_batches_large_lists():
    s = MagicMock()
    s.post.return_value = MagicMock(status_code=201)
    r = BetaPlatformPusher("tok", session=s).push("gitlab", make_assets(450), batch_size=200)
    assert r.assets_count == 450 and s.post.call_count == 3


def test_failed_batch_recorded():
    s = MagicMock()
    s.post.return_value = MagicMock(status_code=500, text="boom")
    r = BetaPlatformPusher("tok", session=s).push("gitlab", make_assets(3))
    assert not r.success and r.assets_count == 0 and len(r.errors) == 1


def test_network_error_recorded_not_raised():
    s = MagicMock()
    s.post.side_effect = requests.ConnectionError("down")
    r = BetaPlatformPusher("tok", session=s).push("gitlab", make_assets(3))
    assert not r.success and "down" in r.errors[0]
