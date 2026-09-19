import json

import pytest

from connectors.servicenow.push import PlatformPusher, PushError


class _Resp:
    def __init__(self, status=202):
        self.status_code = status
        self.text = ""


class FakeSession:
    def __init__(self, status=202):
        self.status = status
        self.posts = []

    def post(self, url, headers=None, json=None, timeout=None):
        self.posts.append((url, headers, json))
        return _Resp(self.status)


def test_push_batches_and_counts():
    sess = FakeSession()
    p = PlatformPusher("https://a/assets", "https://a/exposures", token="t", batch_size=2, session=sess)
    stats = p.push_assets(({"asset_id": f"a{i}"} for i in range(5)))
    assert stats == {"sent": 5, "accepted": 5, "failed": 0}
    assert len(sess.posts) == 3  # 2+2+1


def test_push_sends_bearer_and_payload_shape():
    sess = FakeSession()
    p = PlatformPusher("https://a/assets", "https://a/exposures", token="tok", session=sess)
    p.push_findings(iter([{"finding_id": "f1"}]))
    url, headers, payload = sess.posts[0]
    assert headers["Authorization"] == "Bearer tok"
    assert payload == {"records": [{"finding_id": "f1"}]}


def test_push_failure_raises():
    p = PlatformPusher("https://a/assets", "https://a/exposures", session=FakeSession(status=500))
    with pytest.raises(PushError):
        p.push_assets(iter([{"asset_id": "a1"}]))
